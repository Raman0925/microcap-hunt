"""
meera.py — Technical + price action analysis: Sajal Kapoor style.

6-signal scorecard (max 6 pts):
  Price Position (2 pts):  within 15% of 52w high = 2, 15-30% = 1, >30% = 0
  Revenue Momentum (2 pts): 20%+ YoY growth = 2, 0-20% = 1, declining = 0
  Profit Quality (1 pt):   net profit grew + margin expanded = 1, grew/compressed = 0.5
  PEG Proxy (1 pt):        PE < revenue growth rate = 1

Score >= 4 = pass, 2-3 = borderline, < 2 = reject.
Optionality signals are flagged separately and can influence the debate verdict.
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
    high = _parse_number(company.get("52w_high") or company.get("high_52w"))
    low = _parse_number(company.get("52w_low") or company.get("low_52w"))
    current = _parse_number(company.get("current_price"))

    result: dict = {
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


def _extract_revenue_series(company: dict) -> list[Optional[float]]:
    pl_rows = company.get("profit_loss", [])
    for row in pl_rows:
        label = (list(row.values())[0] if row else "").lower()
        if "sales" in label or "revenue" in label:
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def _extract_net_profit_series(company: dict) -> list[Optional[float]]:
    pl_rows = company.get("profit_loss", [])
    for row in pl_rows:
        label = (list(row.values())[0] if row else "").lower()
        if any(k in label for k in ["net profit", "pat", "profit after tax"]):
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)

    price_pos = _compute_price_position(company)
    revenue = _extract_revenue_series(company)
    net_profits = _extract_net_profit_series(company)

    score = 0.0
    signals: list[str] = []
    notes: list[str] = []
    optionality_signals: list[str] = []

    # ── Signal 1: Price Position (2 pts) — Sajal Kapoor ────────────────────
    from_high = price_pos.get("from_high_pct")
    price_pts = 0
    if from_high is not None:
        if from_high <= 15:
            price_pts = 2
            score += 2
            signals.append(f"Price within {from_high:.1f}% of 52w high — strong momentum")
        elif from_high <= 30:
            price_pts = 1
            score += 1
            signals.append(f"Price within {from_high:.1f}% of 52w high — moderate momentum")
        else:
            notes.append(f"Price {from_high:.1f}% below 52w high — weak price action")
    else:
        notes.append("52w high/low data unavailable")

    # ── Signal 2: Revenue Momentum (2 pts) ─────────────────────────────────
    valid_rev = [v for v in revenue[:3] if v is not None and v > 0]
    revenue_growth_pct: Optional[float] = None
    revenue_momentum = "flat"

    if len(valid_rev) >= 2:
        rev_growth = (valid_rev[0] - valid_rev[1]) / valid_rev[1] * 100
        revenue_growth_pct = round(rev_growth, 1)
        if rev_growth >= 20:
            score += 2
            revenue_momentum = "strong"
            signals.append(f"Revenue +{rev_growth:.1f}% YoY — strong momentum")
        elif rev_growth > 0:
            score += 1
            revenue_momentum = "growing"
            signals.append(f"Revenue +{rev_growth:.1f}% YoY — growing")
        else:
            revenue_momentum = "declining"
            notes.append(f"Revenue {rev_growth:.1f}% YoY — declining")
    else:
        notes.append("Insufficient revenue data")

    # Optionality: deep price weakness + revenue still growing
    if from_high is not None and from_high > 40 and revenue_momentum in ("growing", "strong"):
        optionality_signals.append(
            "Price weakness despite revenue growth — possible Laurus-2023-type optionality"
        )

    # ── Signal 3: Profit Quality (1 pt) ────────────────────────────────────
    profit_growth_pct: Optional[float] = None
    if len(net_profits) >= 2 and len(valid_rev) >= 2:
        np_valid = [v for v in net_profits[:2] if v is not None]
        if len(np_valid) == 2 and np_valid[1] > 0:
            np_growth = (np_valid[0] - np_valid[1]) / np_valid[1] * 100
            profit_growth_pct = round(np_growth, 1)

            if np_growth > 0:
                # Check margin direction
                margin_now = np_valid[0] / valid_rev[0] if valid_rev[0] > 0 else 0
                margin_prev = np_valid[1] / valid_rev[1] if valid_rev[1] > 0 else 0
                if margin_now >= margin_prev:
                    score += 1
                    signals.append(
                        f"Profit +{np_growth:.1f}% YoY with margin expansion — quality growth"
                    )
                else:
                    score += 0.5
                    notes.append(
                        f"Profit grew +{np_growth:.1f}% but margin compressed"
                    )
            else:
                notes.append(f"Net profit declined {np_growth:.1f}% YoY")

    # ── Signal 4: PEG Proxy — Lynch (1 pt) ─────────────────────────────────
    pe_ratio = _parse_number(company.get("pe_ratio") or company.get("pe"))
    if pe_ratio is not None and revenue_growth_pct is not None and revenue_growth_pct > 0:
        if pe_ratio < revenue_growth_pct:
            score += 1
            signals.append(
                f"PE {pe_ratio:.1f} < revenue growth {revenue_growth_pct:.1f}% — undervalued vs growth"
            )
        if pe_ratio < 10 and revenue_growth_pct > 0:
            optionality_signals.append(
                f"Low PE {pe_ratio:.1f} with positive revenue growth — potentially overlooked"
            )

    # ── Optionality from quarterly data ────────────────────────────────────
    quarterly = company.get("quarterly_results") or company.get("quarterly", [])
    if quarterly and revenue_momentum in ("flat", "declining"):
        q_rev = []
        for row in (quarterly if isinstance(quarterly, list) else []):
            label = (list(row.values())[0] if row else "").lower()
            if "sales" in label or "revenue" in label:
                q_rev = [_parse_number(v) for v in list(row.values())[1:]]
                break
        q_valid = [v for v in q_rev[:2] if v is not None and v > 0]
        if len(q_valid) == 2 and q_valid[0] > q_valid[1]:
            optionality_signals.append(
                "Quarter-on-quarter revenue inflecting while annual is flat — possible turnaround"
            )

    # ── Price signal classification ─────────────────────────────────────────
    if price_pts == 2:
        price_signal = "bullish"
    elif price_pts == 1:
        price_signal = "neutral"
    elif optionality_signals:
        price_signal = "optionality"
    else:
        price_signal = "bearish"

    # ── Verdict ─────────────────────────────────────────────────────────────
    score = round(score, 1)

    if score >= 4:
        verdict = "pass"
        confidence = min(0.5 + (score - 4) * 0.1, 0.95)
        entry_zone = "attractive"
    elif score >= 2:
        verdict = "borderline"
        confidence = 0.35 + score * 0.04
        entry_zone = "neutral" if not optionality_signals else "contrarian"
    else:
        verdict = "reject"
        confidence = 0.70 + (2 - score) * 0.05
        entry_zone = "contrarian" if optionality_signals else "weak"

    if verdict == "reject":
        report = (
            f"{name} — weak technical setup (score {score}/6): "
            f"{'; '.join(notes[:2]) or 'no bullish signals'}"
        )
    elif verdict == "borderline":
        report = (
            f"{name} — mixed technical signals (score {score}/6). "
            f"Positives: {', '.join(signals) or 'none'}. "
            f"Concerns: {', '.join(notes) or 'none'}."
        )
    else:
        report = (
            f"{name} — solid technical setup (score {score}/6). "
            f"Signals: {', '.join(signals)}. "
            f"Notes: {', '.join(notes) or 'none'}."
        )

    if optionality_signals:
        report += f" Optionality: {'; '.join(optionality_signals[:2])}."

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "report": report,
        "score": score,
        "price_signal": price_signal,
        "entry_zone": entry_zone,
        "revenue_momentum": revenue_momentum,
        "pe_ratio": pe_ratio,
        "from_high_pct": from_high,
        "revenue_growth_pct": revenue_growth_pct,
        "profit_growth_pct": profit_growth_pct,
        "optionality_signals": optionality_signals,
        "technical_notes": "; ".join(signals + notes),
        "price_position": price_pos,
        "agent": "meera",
    }
