"""
main.py — Project Microcap Hunt orchestrator.

Runs continuously in batches: fetches companies, analyses with three rule-based agents,
debates, and sends reports to Telegram. Supports resuming from saved progress.

No ANTHROPIC_API_KEY required — all analysis is rule-based.
"""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import fetcher
import laxmi
import meera
import tara
import debate
import reporter
import state_tracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("microcap_hunt.log"),
    ],
)
logger = logging.getLogger("main")

DEFAULT_BATCH_SIZE = 20
DEFAULT_MAX_COMPANIES = 500
INTER_BATCH_PAUSE = 30  # seconds between batches


def check_env():
    """Warn about missing environment variables."""
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        logger.warning(
            "TELEGRAM_BOT_TOKEN not set — reports will be logged to stdout only"
        )


def analyse_company(company_data: dict) -> dict:
    """Run all three agents on a single company and run debate. Returns final verdict."""
    symbol = company_data.get("symbol", "UNKNOWN")

    if company_data.get("error"):
        logger.warning(f"Skipping {symbol} — fetch error: {company_data['error']}")
        return {
            "symbol": symbol,
            "name": company_data.get("name", symbol),
            "final_verdict": "reject",
            "confidence": 1.0,
            "report": f"{symbol} — rejected: data fetch failed",
            "debated": False,
            "error": company_data["error"],
        }

    logger.info(f"Analysing {symbol}...")
    cname = company_data.get("name", symbol)

    # Run Laxmi first (primary filter)
    state_tracker.agent_start("laxmi", symbol, cname)
    laxmi_result = laxmi.analyse(company_data)
    state_tracker.agent_done("laxmi", laxmi_result.get("verdict", ""))
    logger.info(f"  Laxmi verdict: {laxmi_result['verdict']} ({laxmi_result['confidence']:.0%})")

    # Hard-reject from Laxmi → skip the other agents
    if laxmi_result["verdict"] == "reject" and laxmi_result["confidence"] >= 0.85:
        logger.info(f"  Skipping Meera/Tara — Laxmi hard rejected {symbol}")
        return {
            "symbol": symbol,
            "name": laxmi_result.get("name", symbol),
            "final_verdict": "reject",
            "confidence": laxmi_result["confidence"],
            "report": laxmi_result["report"],
            "debated": False,
            "laxmi": laxmi_result,
        }

    # Run Meera and Tara in parallel
    state_tracker.agent_start("meera", symbol, cname)
    state_tracker.agent_start("tara", symbol, cname)
    with ThreadPoolExecutor(max_workers=2) as executor:
        meera_future = executor.submit(meera.analyse, company_data)
        tara_future = executor.submit(tara.analyse, company_data)
        meera_result = meera_future.result()
        tara_result = tara_future.result()
    state_tracker.agent_done("meera", meera_result.get("verdict", ""))
    state_tracker.agent_done("tara", tara_result.get("verdict", ""))

    logger.info(f"  Meera verdict: {meera_result['verdict']} ({meera_result['confidence']:.0%})")
    logger.info(f"  Tara verdict: {tara_result['verdict']} ({tara_result['confidence']:.0%})")

    final = debate.debate(laxmi_result, meera_result, tara_result)
    logger.info(
        f"  Final verdict: {final['final_verdict']} "
        f"({'debated' if final.get('debated') else 'fast-track'}, {final['confidence']:.0%})"
    )

    final["laxmi"] = laxmi_result
    final["meera"] = meera_result
    final["tara"] = tara_result

    return final


def load_analyzed_symbols() -> set:
    """Load symbols already analyzed (from dashboard_data.json) so we never re-run them."""
    try:
        import json as _json
        from pathlib import Path as _Path
        sf = _Path(__file__).parent / "dashboard_data.json"
        if sf.exists():
            d = _json.loads(sf.read_text())
            return {c["symbol"] for c in d.get("companies", []) if c.get("symbol")}
    except Exception:
        pass
    return set()


def run_batch(companies: list[dict], batch_num: int, already_done: set) -> list[dict]:
    fresh = [c for c in companies if c.get("symbol", "?") not in already_done]
    skipped = len(companies) - len(fresh)
    if skipped:
        logger.info(f"Skipping {skipped} already-analyzed companies")
    if not fresh:
        logger.info(f"=== Batch {batch_num}: nothing new to analyze ===")
        return []

    logger.info(f"=== Starting batch {batch_num}: {len(fresh)} new companies ===")
    results = []

    for i, company in enumerate(fresh, 1):
        symbol = company.get("symbol", "?")
        logger.info(f"[{i}/{len(fresh)}] Processing {symbol}")
        try:
            result = analyse_company(company)
            results.append(result)
            already_done.add(symbol)
            state_tracker.record_result(result)
            reporter.send_company_report(result)
        except Exception as e:
            logger.error(f"Unexpected error processing {symbol}: {e}", exc_info=True)
            results.append({
                "symbol": symbol,
                "final_verdict": "reject",
                "report": f"{symbol} — rejected: processing error ({e})",
            })

    reporter.send_batch_summary(results, batch_num)
    logger.info(f"=== Batch {batch_num} complete ===")
    return results


def main():
    parser = argparse.ArgumentParser(description="Project Microcap Hunt")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_COMPANIES, help="Max companies to analyse")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Companies per batch")
    parser.add_argument("--no-resume", action="store_true", help="Start fresh, ignore saved progress")
    parser.add_argument("--single", type=str, help="Analyse a single company symbol")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PROJECT MICROCAP HUNT — Starting (rule-based mode)")
    logger.info("=" * 60)

    check_env()

    if args.single:
        import requests as req
        session = req.Session()
        url = f"https://www.screener.in/company/{args.single.upper()}/"
        company_data = fetcher.fetch_company_data(args.single.upper(), url, session)
        result = analyse_company(company_data)
        print("\n" + "=" * 60)
        print(f"VERDICT: {result['final_verdict'].upper()}")
        print(result["report"])
        return

    logger.info(f"Config: max={args.max}, batch_size={args.batch_size}, resume={not args.no_resume}")

    logger.info("Fetching microcap company list and data from Screener.in...")
    companies = fetcher.get_companies_with_data(
        max_companies=args.max,
        resume=not args.no_resume,
    )
    logger.info(f"Loaded {len(companies)} companies with data")

    if not companies:
        logger.error("No companies fetched. Check Screener.in connectivity.")
        sys.exit(1)

    # Load already-analyzed symbols BEFORE init_run so we know what's new
    already_done = load_analyzed_symbols()
    fresh_count = sum(1 for c in companies if c.get("symbol") not in already_done)
    logger.info(f"{len(already_done)} already analyzed, {fresh_count} new companies to process")

    state_tracker.init_run(fresh_count)
    reporter.send_startup_message(fresh_count)

    batch_num = 1
    all_results = []

    for start in range(0, len(companies), args.batch_size):
        batch = companies[start: start + args.batch_size]
        batch_results = run_batch(batch, batch_num, already_done)
        all_results.extend(batch_results)
        batch_num += 1

        if start + args.batch_size < len(companies):
            logger.info(f"Pausing {INTER_BATCH_PAUSE}s before next batch...")
            time.sleep(INTER_BATCH_PAUSE)

    shortlisted = [r for r in all_results if r.get("final_verdict") == "shortlist"]
    borderline = [r for r in all_results if r.get("final_verdict") == "borderline"]
    rejected = [r for r in all_results if r.get("final_verdict") == "reject"]

    logger.info("=" * 60)
    logger.info("HUNT COMPLETE")
    logger.info(f"Total analysed: {len(all_results)}")
    logger.info(f"Shortlisted: {len(shortlisted)}")
    logger.info(f"Borderline: {len(borderline)}")
    logger.info(f"Rejected: {len(rejected)}")
    logger.info("=" * 60)

    if shortlisted:
        logger.info("SHORTLISTED COMPANIES:")
        for r in shortlisted:
            logger.info(f"  ✓ {r.get('name', r.get('symbol'))} ({r.get('symbol')})")


if __name__ == "__main__":
    main()
