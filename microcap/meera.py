"""
meera.py — Meera: Technical analysis (rule-based, no API key needed).

Signals (0-3 score):
  Current price within 30% of 52w high  → bullish signal (+1)
  Revenue growing YoY                    → positive momentum (+1)
  Price above 52w midpoint               → uptrend (+1)

Score 2-3 = pass, 1 = borderline, 0 = reject
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_number(text) -> Optional[float]:
    if text is None:
        return None
    cleaned = re.sub(r"[₹,\s%]", "", str(text))
    try:
        return float(cleaned)
    except ValueError:
        return None


def _compute_price_position(company: dict) -> dict:
    high = company.get("52w_high") or _parse_number(company.get("high_52w", ""))
    low = company.get("52w_low")
    current = _parse_number(company.get("current_price"))

    result = {
        "current_price": current,
        "52w_high": high,
        "52w_low": low,
        "position_pct": None,
        "from_high_pct": None,
    }

    if high and low and current and high != low:
        result["position_pct"] = round((current - low) / (high - low) * 100, 1)
        result["from_high_pct"] = round((high - current) / high * 100, 1)

    return result


def _extract_annual_revenue_series(company: dict) -> list[Optional[float]]:
    """Extract annual revenue from P&L table (most recent first)."""
    pl_rows = company.get("profit_loss", [])
    for row in pl_rows:
        label = list(row.values())[0] if row else ""
        if "sales" in label.lower() or "revenue" in label.lower():
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)

    price_pos = _compute_price_position(company)
    revenue = _extract_annual_revenue_series(company)

    score = 0
    signals = []
    notes = []

    # Signal 1: Price within 30% of 52w high (bullish)
    from_high = price_pos.get("from_high_pct")
    if from_high is not None:
        if from_high <= 30:
            score += 1
            signals.append(f"Price within {from_high:.1f}% of 52w high — bullish")
        else:
            notes.append(f"Price {from_high:.1f}% below 52w high — weak")
    else:
        notes.append("52w high/low data unavailable")

    # Signal 2: Revenue growing YoY (compare most recent 2 years)
    valid_rev = [v for v in revenue[:3] if v is not None and v > 0]
    if len(valid_rev) >= 2:
        if valid_rev[0] > valid_rev[1]:
            score += 1
            growth = (valid_rev[0] - valid_rev[1]) / valid_rev[1] * 100
            signals.append(f"Revenue growing YoY (+{growth:.1f}%)")
        else:
            decline = (valid_rev[1] - valid_rev[0]) / valid_rev[1] * 100
            notes.append(f"Revenue declining YoY (-{decline:.1f}%)")
    else:
        notes.append("Insufficient revenue data to assess trend")

    # Signal 3: Price above 52w midpoint (uptrend confirmation)
    pos_pct = price_pos.get("position_pct")
    if pos_pct is not None:
        if pos_pct > 50:
            score += 1
            signals.append(f"Trading above 52w midpoint ({pos_pct:.1f}% of range)")
        else:
            notes.append(f"Trading below 52w midpoint ({pos_pct:.1f}% of range)")

    # Verdict
    if score >= 2:
        verdict = "pass"
        confidence = 0.5 + (score - 2) * 0.2
        price_signal = "bullish"
    elif score == 1:
        verdict = "borderline"
        confidence = 0.4
        price_signal = "neutral"
    else:
        verdict = "reject"
        confidence = 0.75
        price_signal = "bearish"

    if verdict == "reject":
        report = f"{name} — weak technical picture: {'; '.join(notes[:2]) or 'no bullish signals'}"
    elif verdict == "borderline":
        report = (
            f"{name} shows mixed technical signals (score {score}/3). "
            f"Positive: {', '.join(signals) or 'none'}. "
            f"Concerns: {', '.join(notes) or 'none'}."
        )
    else:
        report = (
            f"{name} has a solid technical setup (score {score}/3). "
            f"Signals: {', '.join(signals)}. "
            f"Notes: {', '.join(notes) or 'none'}."
        )

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": confidence,
        "report": report,
        "price_signal": price_signal,
        "entry_zone": "attractive" if score >= 2 else ("neutral" if score == 1 else "weak"),
        "revenue_momentum": "growing" if (len(valid_rev) >= 2 and valid_rev[0] > valid_rev[1]) else "flat/declining",
        "technical_notes": "; ".join(signals + notes),
        "price_position": price_pos,
        "score": score,
        "agent": "meera",
    }
