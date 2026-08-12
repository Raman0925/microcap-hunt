"""
tara.py — Story/qualitative analysis: Nassim Taleb + Vijay Kedia SMILE + Porinju Veliyath.

Scorecard (max 10 pts):
  SMILE (Vijay Kedia):     0-3 pts  (S+M+L+E sub-scores)
  Taleb Framework:         0-3 pts  (Optionality, Antifragility, Skin, Convexity, Via Negativa)
  Porinju Contrarian:      0-1 pt   (unloved sector + hidden gem)
  Governance:              0-2 pts  (VETO power — pledge > 30% or auditor flag)
  News Sentiment:          0-1 pt

Score >= 6 = pass, 3-5 = borderline, < 3 = reject.
Governance VETO (promoter pledge > 30%) overrides score: verdict=reject, confidence=0.90.
"""

import logging
import re
import time
from typing import Optional
from xml.etree import ElementTree as ET

import requests

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

LARGE_MARKET_SECTORS = {
    "healthcare", "pharma", "pharmaceutical", "defence", "defense",
    "chemicals", "chemical", "logistics", "infrastructure", "infra",
    "it services", "software", "renewables", "renewable", "semiconductor",
    "electronics", "engineering", "auto", "agriculture",
}

UNLOVED_SECTORS = {
    "psu", "textile", "textiles", "auto ancillary", "auto component",
    "chemicals", "chemical", "paper", "sugar", "real estate", "power",
    "cement", "steel", "metal",
}

ASPIRATION_KEYWORDS = [
    "expand", "expansion", "new plant", "capacity addition", "global",
    "exports", "export", "new market", "greenfield", "brownfield",
]

OPTIONALITY_KEYWORDS = [
    "r&d", "new product", "api", "export", "capex for expansion",
    "new facility", "research", "development", "innovation",
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
    try:
        query = f"{company_name} {symbol} stock India"
        encoded = requests.utils.quote(query)
        rss_url = (
            f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"
        )
        resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        time.sleep(RATE_LIMIT)

        if resp.status_code != 200:
            return [], 0, 0

        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:8]

        headlines: list[str] = []
        positive = negative = 0
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


def _check_promoter_pledge(shareholding_raw: str) -> tuple[bool, Optional[float]]:
    """Returns (is_pledged_above_30, pledge_pct)."""
    if not shareholding_raw:
        return False, None
    text = shareholding_raw.lower()
    m = re.search(r"pledge[d]?\s*[:\-]?\s*(\d+\.?\d*)\s*%", text)
    if m:
        pct = float(m.group(1))
        return pct > 30, pct
    return False, None


def _extract_promoter_holding(company: dict) -> Optional[float]:
    """Try direct field first, then parse from shareholding_raw."""
    ph = _parse_number(company.get("promoter_holding"))
    if ph is not None:
        return ph
    raw = company.get("shareholding_raw") or ""
    m = re.search(r"promoter[s]?\s*[:\-]?\s*(\d+\.?\d*)\s*%", raw.lower())
    return float(m.group(1)) if m else None


def _check_sector_risk(about: str) -> tuple[bool, str]:
    if not about:
        return False, "sector unknown"
    about_lower = about.lower()
    for sector in AVOID_SECTORS:
        if sector in about_lower:
            return True, f"operates in high-risk sector: {sector}"
    return False, "sector appears acceptable"


def _check_shell_company(about: str) -> bool:
    if not about:
        return True
    return len(about.strip()) < 80


def _extract_founding_year(about: str) -> Optional[int]:
    m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", about)
    return int(m.group(1)) if m else None


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)
    about = company.get("about") or ""
    about_lower = about.lower()
    shareholding_raw = company.get("shareholding_raw") or ""
    mcap = _parse_number(company.get("market_cap_cr") or company.get("mcap_cr"))

    red_flags: list[str] = []
    positive_catalysts: list[str] = []
    taleb_signals: list[str] = []
    governance_signal = "unknown"

    score = 0.0

    # ── Vijay Kedia SMILE (3 pts) ────────────────────────────────────────────
    smile_score = 0.0

    # S — Small in size
    if mcap is not None and mcap < 500:
        smile_score += 0.5
        positive_catalysts.append(f"Small size (₹{mcap:.0f}cr mcap) — large runway ahead")

    # M — Medium in experience (company > 5 years old)
    founding_year = _extract_founding_year(about_lower)
    if founding_year is not None and (2026 - founding_year) >= 5:
        smile_score += 0.5
        positive_catalysts.append(f"Established company (founded ~{founding_year})")

    # L — Large in aspiration
    if any(kw in about_lower for kw in ASPIRATION_KEYWORDS):
        smile_score += 1.0
        positive_catalysts.append("Growth ambition evident in description")

    # E — Extra-large market potential
    if any(sector in about_lower for sector in LARGE_MARKET_SECTORS):
        smile_score += 1.0
        positive_catalysts.append("Operating in large / growing sector")

    score += smile_score

    # ── Nassim Taleb Framework (3 pts) ───────────────────────────────────────
    taleb_score = 0.0

    # Optionality: building new capabilities while core is stable
    if any(kw in about_lower for kw in OPTIONALITY_KEYWORDS):
        taleb_score += 1.0
        taleb_signals.append("Optionality: capability expansion signals detected")

    # Antifragility: diversification + geography
    segment_kws = ["engineering", "chemicals", "consumer", "pharma", "services", "products"]
    segment_count = sum(1 for kw in segment_kws if kw in about_lower)
    if segment_count >= 2:
        taleb_score += 0.5
        taleb_signals.append("Antifragility: multiple segments / diversified revenue")

    if any(kw in about_lower for kw in ["exports", "global", "international", "overseas"]):
        taleb_score += 0.5
        taleb_signals.append("Antifragility: geographic diversification")

    # Skin in the game: promoter > 50% + no pledging
    promoter_holding = _extract_promoter_holding(company)
    _, pledge_pct = _check_promoter_pledge(shareholding_raw)
    no_pledge = pledge_pct is None or pledge_pct == 0
    if promoter_holding is not None and promoter_holding > 50 and no_pledge:
        taleb_score += 0.5
        taleb_signals.append(f"Skin in game: promoter {promoter_holding:.1f}% + no pledging")

    # Via Negativa: penalise commodity/price-taker/regulatory dependency
    via_neg_kws = ["commodity", "price taker", "regulatory", "government dependent"]
    via_neg_count = sum(about_lower.count(kw) for kw in via_neg_kws)
    if via_neg_count > 2:
        taleb_score -= 0.5
        red_flags.append("Via Negativa: commodity/regulatory dependency signals")

    # Convexity: B2B + B2C revenue mix
    b2c_kws = ["consumer", "retail", "direct", "b2c"]
    b2b_kws = ["industrial", "enterprise", "corporate", "b2b", "institutional"]
    has_b2c = any(kw in about_lower for kw in b2c_kws)
    has_b2b = any(kw in about_lower for kw in b2b_kws)
    if has_b2c and has_b2b:
        taleb_score += 0.5
        taleb_signals.append("Convexity: both B2B and B2C revenue streams")

    taleb_score = max(0.0, taleb_score)
    score += taleb_score

    # Optionality score (0-10) for debate engine
    optionality_score = round(min(10, (taleb_score / 3.0) * 10), 1)

    # ── Porinju Veliyath Contrarian (1 pt) ────────────────────────────────────
    porinju_score = 0.0

    if any(sector in about_lower for sector in UNLOVED_SECTORS):
        porinju_score += 0.5
        positive_catalysts.append("Contrarian: currently unloved/unfollowed sector")

    # ── News sentiment ─────────────────────────────────────────────────────
    logger.info(f"Tara: fetching news for {name} ({symbol})")
    headlines, positive_news, negative_news = _search_news(name, symbol)

    if negative_news > 0:
        red_flags.append(f"{negative_news} negative news headlines detected")
    if positive_news >= 1:
        positive_catalysts.append(f"{positive_news} positive news signals")

    # Hidden gem check: sparse coverage = potentially undiscovered
    if len(headlines) == 0:
        porinju_score += 0.5
        positive_catalysts.append("No recent news coverage — possible hidden gem")
    elif len(headlines) <= 2:
        porinju_score += 0.25

    score += porinju_score

    # ── Governance Quality (2 pts, VETO) ──────────────────────────────────
    is_pledged, pledge_pct = _check_promoter_pledge(shareholding_raw)
    gov_score = 0.0

    if is_pledged:
        red_flags.append("Promoter pledging > 30%")
        governance_signal = "red_flag"
    else:
        governance_signal = "clean"
        if promoter_holding is not None and promoter_holding > 40:
            gov_score += 1.0
        elif promoter_holding is not None:
            gov_score += 0.5

    # Auditor signals
    auditor_flags = ["auditor resigned", "qualified opinion", "emphasis of matter", "going concern"]
    if any(flag in about_lower for flag in auditor_flags):
        red_flags.append("Auditor qualification signals detected")
        governance_signal = "red_flag"
    else:
        gov_score += 0.5

    # Negative news check
    neg_news_kws = ["sebi", "fraud", "scam", "npa", "default", "arrested"]
    has_neg_news = any(kw in " ".join(headlines) for kw in neg_news_kws) or negative_news > 0
    if not has_neg_news:
        gov_score += 0.5
    else:
        red_flags.append(f"Negative governance signals in news")

    score += gov_score

    # ── News sentiment score (1 pt) ────────────────────────────────────────
    if positive_news >= 2:
        score += 1.0
    elif positive_news == 1 and negative_news == 0:
        score += 0.5

    # ── Sector risk check (flags only, not scored) ─────────────────────────
    sector_risky, sector_note = _check_sector_risk(about)
    if sector_risky:
        red_flags.append(sector_note)
    sector_view = "negative" if sector_risky else (
        "positive" if any(s in about_lower for s in LARGE_MARKET_SECTORS) else "neutral"
    )

    # Shell company check
    if _check_shell_company(about):
        red_flags.append("Company description very short or missing — possible shell company")

    # ── VETO check ──────────────────────────────────────────────────────────
    score = round(score, 1)

    if governance_signal == "red_flag":
        return {
            "symbol": symbol,
            "name": name,
            "verdict": "reject",
            "confidence": 0.90,
            "report": f"{name} — GOVERNANCE VETO: {'; '.join(red_flags[:2])}",
            "score": score,
            "red_flags": red_flags,
            "positive_catalysts": positive_catalysts,
            "governance_signal": governance_signal,
            "optionality_score": optionality_score,
            "taleb_signals": taleb_signals,
            "smile_score": round(smile_score, 1),
            "contrarian_angle": ", ".join(s for s in taleb_signals if "Contrarian" in s) or None,
            "sector_view": sector_view,
            "news_used": "; ".join(headlines[:3])[:200],
            "agent": "tara",
        }

    # ── Verdict ─────────────────────────────────────────────────────────────
    if score >= 6:
        verdict = "pass"
        confidence = min(0.50 + (score - 6) * 0.08, 0.95)
    elif score >= 3:
        verdict = "borderline"
        confidence = 0.35 + score * 0.03
    else:
        verdict = "reject"
        confidence = max(0.65, 0.85 - score * 0.05)

    if verdict == "reject":
        report = (
            f"{name} — rejected (score {score}/10): "
            f"{'; '.join(red_flags[:2]) or 'failed qualitative checks'}"
        )
    elif verdict == "borderline":
        report = (
            f"{name} has a mixed narrative (score {score}/10). "
            f"Positives: {', '.join(positive_catalysts[:2]) or 'none'}. "
            f"Red flags: {', '.join(red_flags) or 'none'}. "
            f"Sector: {sector_note}."
        )
    else:
        report = (
            f"{name} has a strong story (score {score}/10). "
            f"Catalysts: {', '.join(positive_catalysts[:3]) or 'none'}. "
            f"Taleb signals: {', '.join(taleb_signals[:2]) or 'none'}. "
            f"Governance: {governance_signal}."
        )

    contrarian_angle = None
    if porinju_score > 0:
        contrarian_parts = []
        if any(s in about_lower for s in UNLOVED_SECTORS):
            contrarian_parts.append("unloved sector")
        if len(headlines) == 0:
            contrarian_parts.append("under-followed")
        if contrarian_parts:
            contrarian_angle = " + ".join(contrarian_parts)

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "report": report,
        "score": score,
        "red_flags": red_flags,
        "positive_catalysts": positive_catalysts,
        "governance_signal": governance_signal,
        "optionality_score": optionality_score,
        "taleb_signals": taleb_signals,
        "smile_score": round(smile_score, 1),
        "contrarian_angle": contrarian_angle,
        "sector_view": sector_view,
        "news_used": "; ".join(headlines[:3])[:200],
        "agent": "tara",
    }
