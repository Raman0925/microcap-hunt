"""
fetcher.py — Scrapes Screener.in for Indian microcap companies and their data.

Handles rate limiting, error recovery, and progress caching.
"""

import time
import json
import logging
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SCREENER_BASE = "https://www.screener.in"
# Using the Piotroski scan as the company source (public screen with many small-cap companies)
MICROCAP_SCREEN_URL = "https://www.screener.in/screens/2/piotroski-scan/"
PROGRESS_FILE = Path(__file__).parent / "progress.json"
RATE_LIMIT_SECONDS = 2.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _get(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        time.sleep(RATE_LIMIT_SECONDS)
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        time.sleep(RATE_LIMIT_SECONDS)
        return None


def fetch_microcap_list(session: requests.Session, max_pages: int = 10) -> list[dict]:
    """Fetch list of microcap companies from Screener.in screening page."""
    companies = []
    page = 1

    while page <= max_pages:
        url = MICROCAP_SCREEN_URL if page == 1 else f"{MICROCAP_SCREEN_URL}?page={page}"
        logger.info(f"Fetching company list page {page}: {url}")
        soup = _get(url, session)
        if soup is None:
            break

        # Try to parse company table rows
        rows = soup.select("table.data-table tbody tr")
        if not rows:
            # Try alternate selectors used on screener
            rows = soup.select("#screener-results table tbody tr")

        if not rows:
            logger.info(f"No rows found on page {page}, stopping list fetch.")
            break

        page_companies = []
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            link_tag = row.find("a")
            if not link_tag:
                continue
            href = link_tag.get("href", "")
            name = link_tag.get_text(strip=True)
            if not href or not name:
                continue
            symbol = href.strip("/").split("/")[-1]
            page_companies.append({
                "name": name,
                "symbol": symbol,
                "url": SCREENER_BASE + href if not href.startswith("http") else href,
            })

        if not page_companies:
            logger.info(f"No companies parsed on page {page}, stopping.")
            break

        companies.extend(page_companies)
        logger.info(f"Page {page}: found {len(page_companies)} companies (total {len(companies)})")
        page += 1

    logger.info(f"Total companies found: {len(companies)}")
    return companies


def _parse_number(text: str) -> Optional[float]:
    """Parse a number string like '1,234.56' or '₹1,234 Cr' into float."""
    if not text:
        return None
    text = re.sub(r"[₹,\s]", "", text)
    text = re.sub(r"(Cr|cr|L|lakh|%)", "", text).strip()
    try:
        return float(text)
    except ValueError:
        return None


def _extract_table_value(soup: BeautifulSoup, label: str) -> Optional[str]:
    """Find a value in Screener's key metrics table by label text."""
    for li in soup.select("ul.company-ratios li, #top-ratios li"):
        name_span = li.find("span", class_="name")
        val_span = li.find("span", class_="value") or li.find("span", class_="number")
        if name_span and val_span:
            if label.lower() in name_span.get_text(strip=True).lower():
                return val_span.get_text(strip=True)
    return None


def _extract_annual_table(soup: BeautifulSoup, section_id: str) -> list[dict]:
    """Extract annual data rows from a section (P&L, Balance Sheet, Cash Flow)."""
    section = soup.find("section", id=section_id)
    if not section:
        return []

    table = section.find("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    rows = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def fetch_company_data(symbol: str, url: str, session: requests.Session) -> dict:
    """Fetch detailed financial data for a single company from Screener.in."""
    logger.info(f"Fetching company data: {symbol}")
    soup = _get(url, session)
    if soup is None:
        return {"symbol": symbol, "error": "fetch_failed"}

    data = {"symbol": symbol, "url": url}

    # Basic info
    name_tag = soup.find("h1")
    data["name"] = name_tag.get_text(strip=True) if name_tag else symbol

    about_section = soup.find("div", class_="company-profile") or soup.find("p", class_="about")
    data["about"] = about_section.get_text(strip=True)[:1000] if about_section else ""

    # Key ratios
    ratio_fields = {
        "market_cap": "Market Cap",
        "current_price": "Current Price",
        "high_52w": "High / Low",
        "pe_ratio": "Stock P/E",
        "book_value": "Book Value",
        "dividend_yield": "Dividend Yield",
        "roce": "ROCE",
        "roe": "ROE",
        "face_value": "Face Value",
        "debt_to_equity": "Debt to equity",
        "promoter_holding": "Promoter holding",
    }
    for key, label in ratio_fields.items():
        data[key] = _extract_table_value(soup, label)

    # Parse 52w high/low from "High / Low" field like "120 / 45"
    hl = data.get("high_52w", "") or ""
    if "/" in hl:
        parts = hl.split("/")
        data["52w_high"] = _parse_number(parts[0])
        data["52w_low"] = _parse_number(parts[1])
    else:
        data["52w_high"] = None
        data["52w_low"] = None

    # Annual P&L data
    pl_rows = _extract_annual_table(soup, "profit-loss")
    data["profit_loss"] = pl_rows

    # Cash flow data
    cf_rows = _extract_annual_table(soup, "cash-flow")
    data["cash_flow"] = cf_rows

    # Balance sheet
    bs_rows = _extract_annual_table(soup, "balance-sheet")
    data["balance_sheet"] = bs_rows

    # Quarterly results
    qr_rows = _extract_annual_table(soup, "quarters")
    data["quarterly_results"] = qr_rows

    # Shareholding pattern - look for promoter %
    sh_section = soup.find("section", id="shareholding")
    if sh_section:
        data["shareholding_raw"] = sh_section.get_text(strip=True)[:500]

    return data


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except Exception:
            pass
    return {"completed": [], "companies": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def get_companies_with_data(
    max_companies: int = 50,
    resume: bool = True,
) -> list[dict]:
    """
    Main entry point: returns list of companies with full financial data.
    Fetches from Screener.in, caches progress to disk.
    """
    session = requests.Session()
    progress = load_progress() if resume else {"completed": [], "companies": []}

    completed_symbols = set(progress.get("completed", []))
    known_companies = {c["symbol"]: c for c in progress.get("companies", [])}

    # Fetch company list if we don't have enough
    if len(known_companies) < max_companies:
        logger.info("Fetching microcap company list from Screener.in...")
        company_list = fetch_microcap_list(session)
        for c in company_list:
            if c["symbol"] not in known_companies:
                known_companies[c["symbol"]] = c
        progress["companies"] = list(known_companies.values())
        save_progress(progress)

    # Take up to max_companies symbols, always advancing past already-completed ones
    # so each run fetches FRESH companies, not the same ones again
    all_company_syms = [c["symbol"] for c in progress["companies"]]
    # Put uncompleted companies first (they come after the completed frontier)
    uncompleted = [s for s in all_company_syms if s not in completed_symbols]
    completed_list = [s for s in all_company_syms if s in completed_symbols]
    # Return completed (cached) + up to max_companies new ones
    all_symbols = completed_list + uncompleted[:max(max_companies, len(uncompleted))]
    # Limit to max_companies total to keep batches manageable
    # But always include at least some new ones
    new_to_fetch = uncompleted[:max_companies]
    all_symbols = list(completed_symbols) + new_to_fetch  # cached + fresh
    results = []

    for symbol in all_symbols:
        if symbol in completed_symbols:
            # Load cached result if available
            cached = next(
                (c for c in progress.get("results", []) if c.get("symbol") == symbol),
                None,
            )
            if cached:
                results.append(cached)
            continue

        company = known_companies.get(symbol, {})
        url = company.get("url", f"{SCREENER_BASE}/company/{symbol}/")
        data = fetch_company_data(symbol, url, session)
        results.append(data)

        completed_symbols.add(symbol)
        progress["completed"] = list(completed_symbols)
        if "results" not in progress:
            progress["results"] = []
        # Update or append
        existing = next((i for i, r in enumerate(progress["results"]) if r.get("symbol") == symbol), None)
        if existing is not None:
            progress["results"][existing] = data
        else:
            progress["results"].append(data)

        save_progress(progress)
        logger.info(f"Saved progress: {len(completed_symbols)}/{len(all_symbols)} done")

    return results
