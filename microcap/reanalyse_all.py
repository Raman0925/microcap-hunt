"""Re-run all agents on cached raw data from progress.json using the upgraded framework.

Writes results to SQLite (via db.upsert_company) AND to per-company result files
(results/<SYMBOL>.json) so the FastAPI detail endpoint returns the full nested data.
News fetching in Tara is skipped for speed (raw data already cached).
"""
import datetime
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import db
import laxmi as laxmi_agent
import meera as meera_agent
import tara as tara_agent
import debate as debate_agent

# Skip Google News HTTP calls during bulk re-analysis (197+ companies would rate-limit).
tara_agent._search_news = lambda name, sym: ([], 0, 0)

db.init_db()

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def parse_market_cap_cr(mc_str):
    """'₹2,646Cr.' / '₹161Cr.' / '₹19,500 Cr' -> float crores."""
    if mc_str is None:
        return None
    if isinstance(mc_str, (int, float)):
        return float(mc_str)
    s = re.sub(r"[₹,\s]", "", str(mc_str)).lower().rstrip(".")
    if s.endswith("cr"):
        s = s[:-2]
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


pf = Path(__file__).parent / "progress.json"
if not pf.exists():
    print("progress.json not found")
    sys.exit(1)

raw = json.loads(pf.read_text())
raw_results = {r["symbol"]: r for r in raw.get("results", []) if r.get("symbol")}
print(f"Re-analyzing {len(raw_results)} companies with upgraded framework...")

updated = 0
errors = 0
now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

for sym, company_data in raw_results.items():
    try:
        # Ensure market_cap_cr is available (raw data only has the string form).
        mc_cr = company_data.get("market_cap_cr") or parse_market_cap_cr(
            company_data.get("market_cap")
        )
        if mc_cr is not None:
            company_data["market_cap_cr"] = mc_cr

        laxmi_r = laxmi_agent.analyse(company_data)
        meera_r = meera_agent.analyse(company_data)
        tara_r = tara_agent.analyse(company_data)
        final = debate_agent.debate(laxmi_r, meera_r, tara_r)

        url = company_data.get("url") or f"https://www.screener.in/company/{sym}/"

        result = {
            **final,
            "laxmi": laxmi_r,
            "meera": meera_r,
            "tara": tara_r,
            "market_cap": company_data.get("market_cap", ""),
            "market_cap_cr": mc_cr,
            "screener_url": url,
            "analyzed_at": now_iso,
        }

        db.upsert_company(result)

        # Write per-company result file for the detail endpoint (full nested data).
        report = final.get("report", "")
        verdict_reason = report.split("\n", 1)[0] if report else ""
        file_data = {
            "symbol": sym,
            "name": company_data.get("name", sym),
            "sector": company_data.get("sector", ""),
            "market_cap": company_data.get("market_cap", ""),
            "market_cap_cr": mc_cr,
            "description": company_data.get("about", ""),
            "screener_url": url,
            "verdict": final.get("final_verdict"),
            "confidence": final.get("confidence"),
            "verdict_reason": verdict_reason,
            "verdict_memo": report,
            "investment_thesis": final.get("investment_thesis", ""),
            "debate_reasoning": final.get("debate_reasoning", []),
            "vote_tally": final.get("vote_tally", {}),
            "laxmi": laxmi_r,
            "meera": meera_r,
            "tara": tara_r,
            "analyzed_at": now_iso,
        }
        (RESULTS_DIR / f"{sym}.json").write_text(json.dumps(file_data, indent=2))

        updated += 1
        if updated % 20 == 0:
            print(f"  {updated}/{len(raw_results)} done...")
    except Exception as e:
        print(f"  Error on {sym}: {e}")
        errors += 1

print(f"\nDone. Updated: {updated}, Errors: {errors}")
print("DB stats:", db.get_stats())
