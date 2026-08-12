"""
tara.py — Tara: Story/narrative analysis (rule-based + Google News RSS, no API key needed).

Checks:
  - Promoter pledging > 30%              → red flag (reject)
  - Sector is PSU bank / high-debt sector → caution
  - Recent news mentions (count)          → gauge sentiment
  - About text quality check              → flag shell-company-like descriptions
"""

import logging
import re
import time
from typing import Optional
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RATE_LIMIT = 2.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

AVOID_SECTORS = {
    "psu bank", "public sector bank", "state bank", "nationalised bank",
    "housing finance", "microfinance", "chit fund",
}

NEGATIVE_KEYWORDS = [
    "fraud", "scam", "sebi", "regulatory action", "bankruptcy", "insolvency",
    "defaulted", "npa", "wilful default", "promoter arrested", "cci",
]

POSITIVE_KEYWORDS = [
    "order win", "contract", "expansion", "record profit", "strong growth",
    "acquisition", "new plant", "capex", "export", "turnaround",
]


def _parse_number(text) -> Optional[float]:
    if text is None:
        return None
    cleaned = re.sub(r"[₹,\s%]", "", str(text))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _search_news(company_name: str, symbol: str) -> tuple[list[str], int, int]:
    """
    Fetch Google News RSS headlines. Returns (headlines, positive_count, negative_count).
    """
    try:
        query = f"{company_name} {symbol} stock India"
        encoded = requests.utils.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        time.sleep(RATE_LIMIT)

        if resp.status_code != 200:
            return [], 0, 0

        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:8]

        headlines = []
        positive = 0
        negative = 0
        for item in items:
            title = item.findtext("title", "").lower()
            if title:
                headlines.append(title)
                if any(kw in title for kw in POSITIVE_KEYWORDS):
                    positive += 1
                if any(kw in title for kw in NEGATIVE_KEYWORDS):
                    negative += 1

        return headlines, positive, negative
    except Exception as e:
        logger.warning(f"News search failed for {company_name}: {e}")
        return [], 0, 0


def _check_promoter_pledge(shareholding_raw: str) -> bool:
    """Returns True if promoter pledging > 30% is detected."""
    if not shareholding_raw:
        return False
    text = shareholding_raw.lower()
    match = re.search(r"pledge[d]?\s*[:\-]?\s*(\d+\.?\d*)\s*%", text)
    if match:
        pct = float(match.group(1))
        return pct > 30
    return False


def _check_sector_risk(about: str) -> tuple[bool, str]:
    """Returns (is_risky_sector, sector_note)."""
    if not about:
        return False, "sector unknown"
    about_lower = about.lower()
    for sector in AVOID_SECTORS:
        if sector in about_lower:
            return True, f"operates in high-risk sector: {sector}"
    return False, "sector appears acceptable"


def _check_shell_company(about: str) -> bool:
    """Flag suspiciously short or vague company descriptions."""
    if not about:
        return True
    stripped = about.strip()
    return len(stripped) < 80


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)
    about = company.get("about") or ""
    shareholding_raw = company.get("shareholding_raw") or ""

    red_flags = []
    positive_catalysts = []
    governance_signal = "unknown"

    # Check promoter pledge
    if _check_promoter_pledge(shareholding_raw):
        red_flags.append("Promoter pledging > 30%")
        governance_signal = "red_flag"
    else:
        governance_signal = "clean"

    # Sector risk
    sector_risky, sector_note = _check_sector_risk(about)
    if sector_risky:
        red_flags.append(sector_note)
    sector_view = "negative" if sector_risky else "neutral"

    # Shell company check
    if _check_shell_company(about):
        red_flags.append("Company description very short or missing — possible shell")

    # News sentiment
    logger.info(f"Tara: fetching news for {name} ({symbol})")
    headlines, positive_news, negative_news = _search_news(name, symbol)

    if negative_news > 0:
        red_flags.append(f"{negative_news} negative news headlines detected")
    if positive_news > 0:
        positive_catalysts.append(f"{positive_news} positive news signals found")
    if len(headlines) > 3:
        positive_catalysts.append(f"Active news coverage ({len(headlines)} recent articles)")
    elif len(headlines) == 0:
        red_flags.append("No recent news coverage found")

    # Verdict
    if red_flags and governance_signal == "red_flag":
        verdict = "reject"
        confidence = 0.85
    elif len(red_flags) >= 2:
        verdict = "reject"
        confidence = 0.75
    elif len(red_flags) == 1:
        verdict = "borderline"
        confidence = 0.5
    else:
        verdict = "pass"
        confidence = 0.55 + min(positive_news * 0.05, 0.2)

    if verdict == "reject":
        report = f"{name} — rejected: {'; '.join(red_flags[:2])}"
    elif verdict == "borderline":
        report = (
            f"{name} has a mixed narrative. "
            f"Red flags: {', '.join(red_flags) or 'none'}. "
            f"Positives: {', '.join(positive_catalysts) or 'none'}. "
            f"Sector: {sector_note}."
        )
    else:
        report = (
            f"{name} has a clean story. "
            f"Positive signals: {', '.join(positive_catalysts) or 'none found'}. "
            f"{sector_note.capitalize()}. Governance: {governance_signal}."
        )

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": confidence,
        "report": report,
        "red_flags": red_flags,
        "positive_catalysts": positive_catalysts,
        "sector_view": sector_view,
        "narrative_score": max(1, min(10, 5 + positive_news - len(red_flags) * 2)),
        "governance_signal": governance_signal,
        "news_used": "; ".join(headlines[:3])[:200],
        "agent": "tara",
    }
