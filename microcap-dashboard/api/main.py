import json
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Microcap Hunt API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MICROCAP_DIR = Path("/home/openclaw/.openclaw/workspace/microcap")
RESULTS_DIR = MICROCAP_DIR / "results"
PROGRESS_FILE = MICROCAP_DIR / "progress.json"
DASHBOARD_STATE_FILE = MICROCAP_DIR / "dashboard_data.json"

# Add microcap dir to path so we can import db
sys.path.insert(0, str(MICROCAP_DIR))

try:
    import db as _db
    _db.init_db()
    _DB_AVAILABLE = True
except Exception:
    _DB_AVAILABLE = False

def normalise_verdict(v):
    if not v:
        return 'unknown'
    v = str(v).lower().strip()
    if v in ('shortlist', 'shortlisted'):
        return 'shortlisted'
    if v in ('reject', 'rejected', 'auto_rejected_fraud_veto'):
        return 'rejected'
    if v in ('pass', 'borderline'):
        return v
    return v


def parse_market_cap_cr(market_cap_str):
    """Parse market cap string like '₹19,500 Cr' to a float."""
    if market_cap_str is None:
        return None
    if isinstance(market_cap_str, (int, float)):
        return float(market_cap_str)
    s = str(market_cap_str)
    s = s.replace('₹', '').replace(',', '').replace(' ', '').lower()
    # strip 'cr' suffix
    if s.endswith('cr'):
        s = s[:-2]
    try:
        return float(s)
    except (ValueError, TypeError):
        return None




def _db_has_data() -> bool:
    if not _DB_AVAILABLE:
        return False
    try:
        stats = _db.get_stats()
        return stats["total"] > 0
    except Exception:
        return False


def read_live_agent_status():
    """Read live agent status — prefer SQLite, fall back to dashboard_data.json."""
    if _DB_AVAILABLE:
        try:
            activity = _db.get_agent_activity()
            if activity:
                agents = {}
                for name, info in activity.items():
                    agents[name] = {
                        "status": info.get("status", "idle"),
                        "current": info.get("current_symbol"),
                        "current_company": info.get("current_company"),
                        "analyzed_today": info.get("count", 0),
                        "last_verdict": info.get("last_verdict"),
                    }
                return agents
        except Exception:
            pass

    # Fallback: dashboard_data.json
    if not DASHBOARD_STATE_FILE.exists():
        return None
    try:
        with open(DASHBOARD_STATE_FILE) as f:
            data = json.load(f)
        activity = data.get("agent_activity", {})
        agents = {}
        for name, info in activity.items():
            status = info.get("status", "idle")
            last_company = info.get("last_company", "")
            current = None
            current_company = None
            if last_company and "(" in last_company:
                parts = last_company.rsplit("(", 1)
                current_company = parts[0].strip()
                current = parts[1].rstrip(")").strip()
            elif last_company:
                current = last_company
                current_company = last_company
            agents[name] = {
                "status": status,
                "current": current,
                "current_company": current_company,
                "analyzed_today": info.get("count", 0),
                "last_verdict": info.get("last_verdict"),
            }
        return agents
    except Exception:
        return None


def read_progress():
    if not PROGRESS_FILE.exists():
        return {
            "total": 1840, "analyzed": 0, "shortlisted": 0,
            "rejected": 0, "borderline": 0,
            "agents": {
                "laxmi": {"status": "idle", "current": None},
                "meera": {"status": "idle", "current": None},
                "tara": {"status": "idle", "current": None},
            },
            "last_updated": "never",
        }
    with open(PROGRESS_FILE) as f:
        data = json.load(f)
    live = read_live_agent_status()
    if live:
        data["agents"] = live
    return data


def _build_result_file_index() -> dict:
    """Build a symbol→{market_cap_cr, laxmi_score, ...} index from individual result files."""
    index = {}
    if not RESULTS_DIR.exists():
        return index
    for path in RESULTS_DIR.glob("*.json"):
        if any(path.stem.endswith(f"_{a}") for a in ("laxmi", "meera", "tara", "debate")):
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            sym = data.get("symbol", path.stem)
            mc_str = data.get("market_cap", "")
            mc_cr = data.get("market_cap_cr") or parse_market_cap_cr(mc_str)
            index[sym] = {
                "market_cap": mc_str,
                "market_cap_cr": mc_cr,
                "laxmi_score": data.get("laxmi", {}).get("score") or data.get("laxmi_score"),
                "meera_score": data.get("meera", {}).get("score") or data.get("meera_score"),
                "tara_score": data.get("tara", {}).get("score") or data.get("tara_score"),
                "optionality_score": data.get("optionality", {}).get("score") or data.get("optionality_score"),
            }
        except Exception:
            pass
    return index


def _apply_result_overlay(companies: list) -> list:
    """Overlay market_cap and agent scores from individual result files."""
    result_index = _build_result_file_index()
    if not result_index:
        return companies
    for c in companies:
        overlay = result_index.get(c["symbol"])
        if not overlay:
            continue
        if not c.get("market_cap_cr") and overlay.get("market_cap_cr"):
            c["market_cap_cr"] = overlay["market_cap_cr"]
            c["market_cap"] = overlay.get("market_cap", "")
        for key in ("laxmi_score", "meera_score", "tara_score", "optionality_score"):
            if c.get(key) is None and overlay.get(key) is not None:
                c[key] = overlay[key]
    return companies


def read_all_companies():
    # Primary: SQLite
    if _db_has_data():
        try:
            rows = _db.get_all_companies()
            companies = [_normalize_db_row(r) for r in rows]
            return _apply_result_overlay(companies)
        except Exception:
            pass

    # Fallback: JSON files
    return _read_companies_from_json()


def read_companies_page(page: int = 1, limit: int = 50, verdict: str | None = None):
    """Return (companies, total) for one page, filtered by normalized verdict."""
    page = max(1, page)
    limit = max(1, limit)
    offset = (page - 1) * limit
    norm_verdict = normalise_verdict(verdict) if verdict else None
    if norm_verdict in (None, "all", "unknown"):
        norm_verdict = None

    # Primary: SQLite with LIMIT/OFFSET
    if _db_has_data():
        try:
            total = _db.get_companies_count(norm_verdict)
            rows = _db.get_all_companies(limit=limit, offset=offset, verdict=norm_verdict)
            companies = _apply_result_overlay([_normalize_db_row(r) for r in rows])
            return companies, total
        except Exception:
            pass

    # Fallback: JSON files (paginate in memory)
    all_c = _read_companies_from_json()
    if norm_verdict:
        all_c = [c for c in all_c if c["verdict"] == norm_verdict]
    total = len(all_c)
    return all_c[offset:offset + limit], total


def _parse_json_list(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val)
    except Exception:
        return []


def _normalize_db_row(row: dict) -> dict:
    mc_str = row.get("market_cap", "")
    mc_cr = row.get("market_cap_cr") or parse_market_cap_cr(mc_str)
    return {
        "symbol": row.get("symbol", ""),
        "name": row.get("name", ""),
        "sector": row.get("sector", ""),
        "market_cap": mc_str,
        "market_cap_cr": mc_cr,
        "verdict": normalise_verdict(row.get("verdict", "unknown")),
        "confidence": row.get("confidence"),
        "analyzed_at": row.get("analyzed_at", ""),
        "report": row.get("report", ""),
        "screener_url": row.get("screener_url", ""),
        "laxmi_verdict": normalise_verdict(row.get("laxmi_verdict", "")),
        "meera_verdict": normalise_verdict(row.get("meera_verdict", "")),
        "tara_verdict": normalise_verdict(row.get("tara_verdict", "")),
        "investment_thesis": row.get("investment_thesis", ""),
        "laxmi_score": row.get("laxmi_score"),
        "meera_score": row.get("meera_score"),
        "tara_score": row.get("tara_score"),
        "optionality_score": row.get("optionality_score"),
        # Upgraded-framework fields
        "debate_reasoning": _parse_json_list(row.get("debate_reasoning")),
        "taleb_signals": _parse_json_list(row.get("taleb_signals")),
        "optionality_signals": _parse_json_list(row.get("optionality_signals")),
        "key_strengths": _parse_json_list(row.get("key_strengths")),
        "key_risks": _parse_json_list(row.get("key_risks")),
        "forensic_flags": _parse_json_list(row.get("red_flags") or row.get("forensic_flags")),
        "smile_score": row.get("smile_score"),
        "contrarian_angle": row.get("contrarian_angle"),
        "revenue_growth_pct": row.get("revenue_growth_pct"),
        "profit_growth_pct": row.get("profit_growth_pct"),
        "pe_ratio": row.get("pe_ratio"),
        "cfo_to_ebitda": row.get("cfo_to_ebitda"),
        "owner_earnings": row.get("owner_earnings"),
        "revenue_growth_years": row.get("revenue_growth_years"),
    }


def _read_companies_from_json() -> list:
    seen = {}

    if DASHBOARD_STATE_FILE.exists():
        try:
            with open(DASHBOARD_STATE_FILE) as f:
                dash = json.load(f)
            for c in dash.get("companies", []):
                sym = c.get("symbol", "")
                if not sym:
                    continue
                mc_str = c.get("market_cap", "")
                mc_cr = c.get("market_cap_cr") or parse_market_cap_cr(mc_str)
                seen[sym] = {
                    "symbol": sym,
                    "name": c.get("name", sym),
                    "sector": c.get("sector", ""),
                    "market_cap": mc_str,
                    "market_cap_cr": mc_cr,
                    "verdict": normalise_verdict(c.get("verdict", "unknown")),
                    "confidence": c.get("confidence"),
                    "analyzed_at": c.get("timestamp", ""),
                    "report": c.get("report", ""),
                    "screener_url": c.get("screener_url", f"https://www.screener.in/company/{sym}/"),
                    "laxmi_verdict": normalise_verdict(c.get("laxmi_verdict", "")),
                    "meera_verdict": normalise_verdict(c.get("meera_verdict", "")),
                    "tara_verdict": normalise_verdict(c.get("tara_verdict", "")),
                    "investment_thesis": c.get("investment_thesis", ""),
                    "laxmi_score": c.get("laxmi", {}).get("score") or c.get("laxmi_score"),
                    "meera_score": c.get("meera", {}).get("score") or c.get("meera_score"),
                    "tara_score": c.get("tara", {}).get("score") or c.get("tara_score"),
                    "optionality_score": c.get("optionality", {}).get("score") or c.get("optionality_score"),
                }
        except Exception:
            pass

    if RESULTS_DIR.exists():
        for path in sorted(RESULTS_DIR.glob("*.json")):
            if any(path.stem.endswith(f"_{a}") for a in ("laxmi", "meera", "tara", "debate")):
                continue
            try:
                with open(path) as f:
                    data = json.load(f)
                sym = data.get("symbol", path.stem)
                mc_str = data.get("market_cap", "")
                mc_cr = data.get("market_cap_cr") or parse_market_cap_cr(mc_str)
                entry = {
                    "symbol": sym,
                    "name": data.get("name") or data.get("company", ""),
                    "sector": data.get("sector", ""),
                    "market_cap": mc_str,
                    "market_cap_cr": mc_cr,
                    "verdict": normalise_verdict(data.get("verdict", "unknown")),
                    "confidence": data.get("confidence"),
                    "analyzed_at": data.get("analyzed_at", ""),
                    "report": data.get("report", ""),
                    "screener_url": f"https://www.screener.in/company/{sym}/",
                    "laxmi_verdict": normalise_verdict(data.get("laxmi", {}).get("verdict", "")),
                    "meera_verdict": normalise_verdict(data.get("meera", {}).get("verdict", "")),
                    "tara_verdict": normalise_verdict(data.get("tara", {}).get("verdict", "")),
                    "investment_thesis": data.get("investment_thesis", ""),
                    "laxmi_score": data.get("laxmi", {}).get("score") or data.get("laxmi_score"),
                    "meera_score": data.get("meera", {}).get("score") or data.get("meera_score"),
                    "tara_score": data.get("tara", {}).get("score") or data.get("tara_score"),
                    "optionality_score": data.get("optionality", {}).get("score") or data.get("optionality_score"),
                }
                seen[sym] = entry
            except Exception:
                pass

    return sorted(seen.values(), key=lambda c: str(c.get("analyzed_at") or ""), reverse=True)


@app.get("/api/progress")
def get_progress():
    # Fast path: get all counts from SQLite — never touch the 38 MB progress.json
    if _db_has_data():
        analyzed = _db.get_companies_count()
        shortlisted = _db.get_companies_count("shortlisted")
        borderline = _db.get_companies_count("borderline")
        rejected = _db.get_companies_count("rejected")
        agents = read_live_agent_status() or {}
        return {
            "total": 2123,
            "analyzed": analyzed,
            "shortlisted": shortlisted,
            "borderline": borderline,
            "rejected": rejected,
            "agents": agents,
            "last_updated": "live",
        }
    # Fallback: parse progress.json (slow, only if DB unavailable)
    data = read_progress()
    companies = read_all_companies()
    verdicts = [c["verdict"] for c in companies]
    data["analyzed"] = len(companies)
    data["shortlisted"] = verdicts.count("shortlisted") + verdicts.count("shortlist")
    data["borderline"] = verdicts.count("borderline")
    data["rejected"] = verdicts.count("rejected") + verdicts.count("reject")
    return data


@app.get("/api/companies")
def get_companies(page: int = 1, limit: int = 50, verdict: str | None = None):
    companies, total = read_companies_page(page, limit, verdict)
    pages = max(1, -(-total // limit)) if limit else 1  # ceil division
    return {
        "companies": companies,
        "total": total,
        "page": max(1, page),
        "pages": pages,
        "limit": limit,
    }


@app.get("/api/company/{symbol}")
def get_company(symbol: str):
    sym = symbol.upper()

    # Prefer individual result file — it has full nested laxmi/meera/tara objects
    path = RESULTS_DIR / f"{sym}.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        # Normalise: ensure top-level verdict field is present
        if "verdict" not in data and "final_verdict" in data:
            data["verdict"] = data["final_verdict"]
        data["verdict"] = normalise_verdict(data.get("verdict"))
        if "laxmi" in data:
            data["laxmi"]["verdict"] = normalise_verdict(data["laxmi"].get("verdict"))
        if "meera" in data:
            data["meera"]["verdict"] = normalise_verdict(data["meera"].get("verdict"))
        if "tara" in data:
            data["tara"]["verdict"] = normalise_verdict(data["tara"].get("verdict"))
        return data

    # Fall back to SQLite (flat record — frontend will show partial data)
    if _DB_AVAILABLE:
        try:
            row = _db.get_company(sym)
            if row:
                # Reconstruct nested objects from flat fields so frontend works
                row["laxmi"] = {
                    "verdict": row.get("laxmi_verdict", ""),
                    "score": row.get("laxmi_score"),
                    "fcf_positive_years": row.get("fcf_positive_years"),
                    "roce_5yr_avg": row.get("roce_5yr_avg"),
                    "debt_equity": row.get("debt_equity"),
                    "promoter_holding": row.get("promoter_holding_pct"),
                    "promoter_pledge_pct": row.get("promoter_pledging_pct"),
                    "inventory_days": row.get("inventory_days"),
                    "receivable_days": row.get("receivable_days"),
                    "cash_conversion_cycle": row.get("cash_conversion_cycle"),
                    "cfo_to_ebitda": row.get("cfo_to_ebitda"),
                    "owner_earnings": row.get("owner_earnings"),
                    "revenue_growth_years": row.get("revenue_growth_years"),
                    "key_strengths": _parse_json_list(row.get("key_strengths")),
                    "key_risks": _parse_json_list(row.get("key_risks")),
                }
                row["meera"] = {
                    "verdict": row.get("meera_verdict", ""),
                    "score": row.get("meera_score"),
                    "revenue_growth_pct": row.get("revenue_growth_pct"),
                    "profit_growth_pct": row.get("profit_growth_pct"),
                    "pe_ratio": row.get("pe_ratio"),
                    "optionality_signals": _parse_json_list(row.get("optionality_signals")),
                }
                row["tara"] = {
                    "verdict": row.get("tara_verdict", ""),
                    "score": row.get("tara_score"),
                    "smile_score": row.get("smile_score"),
                    "taleb_signals": _parse_json_list(row.get("taleb_signals")),
                    "contrarian_angle": row.get("contrarian_angle"),
                }
                row["debate_reasoning"] = _parse_json_list(row.get("debate_reasoning"))
                row["investment_thesis"] = row.get("investment_thesis", "")
                row["verdict"] = normalise_verdict(row.get("verdict"))
                return row
        except Exception:
            pass

    # Fall back to dashboard_data.json
    if DASHBOARD_STATE_FILE.exists():
        try:
            with open(DASHBOARD_STATE_FILE) as f:
                dash = json.load(f)
            for c in dash.get("companies", []):
                if c.get("symbol", "").upper() == sym:
                    return c
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Company {sym} not found")


@app.get("/api/shortlisted")
def get_shortlisted():
    return [c for c in read_all_companies() if c["verdict"] in ("shortlisted", "shortlist")]


@app.get("/api/agents")
def get_agents():
    data = read_progress()
    return data.get("agents", {})


# Serve React frontend — must come after all /api routes
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(_FRONTEND_DIST / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
