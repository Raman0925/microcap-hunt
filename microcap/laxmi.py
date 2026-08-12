"""
laxmi.py — Laxmi: Fundamental analysis (rule-based, no API key needed).

Scoring:
  FCF positive 3+ of last 5 years  → +1
  Debt/Equity < 1                   → +1
  ROCE > 12%                        → +1
  Promoter holding > 35%            → +1

Score 3-4 = pass, 1-2 = borderline, 0 = reject
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


def _extract_fcf_series(company: dict) -> list[Optional[float]]:
    """Extract free cash flow values from cash flow table."""
    cf_rows = company.get("cash_flow", [])
    for row in cf_rows:
        label = list(row.values())[0] if row else ""
        if "free cash" in label.lower() or "fcf" in label.lower():
            values = []
            for v in list(row.values())[1:]:
                values.append(_parse_number(v))
            return values
    return []


def _extract_revenue_series(company: dict) -> list[Optional[float]]:
    """Extract annual revenue/sales values from P&L table."""
    pl_rows = company.get("profit_loss", [])
    for row in pl_rows:
        label = list(row.values())[0] if row else ""
        if "sales" in label.lower() or "revenue" in label.lower():
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def _extract_working_capital(company: dict) -> dict:
    """Extract inventory days, receivable days, payable days from balance sheet / P&L."""
    bs_rows = company.get("balance_sheet", [])
    pl_rows = company.get("profit_loss", [])

    def _row_last(rows, *labels):
        for row in rows:
            label = (list(row.values())[0] if row else "").lower()
            if any(lbl in label for lbl in labels):
                vals = [_parse_number(v) for v in list(row.values())[1:] if v]
                clean = [v for v in vals if v is not None]
                return clean[-1] if clean else None
        return None

    inventory = _row_last(bs_rows, "inventories", "inventory")
    receivables = _row_last(bs_rows, "trade receivable", "debtors", "receivable")
    payables = _row_last(bs_rows, "trade payable", "creditors", "payable")
    revenue = _row_last(pl_rows, "sales", "revenue")

    inv_days = recv_days = pay_days = None
    if revenue and revenue > 0:
        daily_rev = revenue / 365
        if inventory is not None:
            inv_days = round(inventory / daily_rev, 1)
        if receivables is not None:
            recv_days = round(receivables / daily_rev, 1)
        if payables is not None:
            pay_days = round(payables / daily_rev, 1)

    return {
        "inventory_days": inv_days,
        "receivable_days": recv_days,
        "payable_days": pay_days,
    }


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)

    score = 0
    reasons = []
    risks = []

    # 1. FCF consistency (3+ positive of last 5 years)
    fcf = _extract_fcf_series(company)
    fcf_positive_years = None
    if fcf:
        recent = [v for v in fcf[:5] if v is not None]
        positive_count = sum(1 for v in recent if v > 0)
        fcf_positive_years = positive_count
        if positive_count >= 3:
            score += 1
            reasons.append(f"FCF positive {positive_count}/{len(recent)} years")
        else:
            risks.append(f"FCF inconsistent ({positive_count}/{len(recent)} years positive)")
    else:
        risks.append("FCF data unavailable — cannot verify cash generation")

    # 2. Debt/Equity < 1
    de = _parse_number(company.get("debt_to_equity"))
    if de is not None:
        if de < 1:
            score += 1
            reasons.append(f"Low D/E ratio: {de:.2f}")
        else:
            risks.append(f"High D/E ratio: {de:.2f}")
    else:
        risks.append("D/E ratio not available")

    # 3. ROCE > 12%
    roce = _parse_number(company.get("roce"))
    if roce is not None:
        if roce > 12:
            score += 1
            reasons.append(f"ROCE {roce:.1f}% > 12%")
        else:
            risks.append(f"Low ROCE: {roce:.1f}%")
    else:
        risks.append("ROCE not available")

    # 4. Promoter holding > 35%
    ph = _parse_number(company.get("promoter_holding"))
    if ph is not None:
        if ph > 35:
            score += 1
            reasons.append(f"Promoter holding {ph:.1f}% > 35%")
        else:
            risks.append(f"Low promoter holding: {ph:.1f}%")
    else:
        risks.append("Promoter holding data not available")

    # Working capital metrics
    wc = _extract_working_capital(company)

    # Verdict
    if score >= 3:
        verdict = "pass"
        confidence = 0.5 + (score - 3) * 0.2
    elif score >= 1:
        verdict = "borderline"
        confidence = 0.3 + score * 0.1
    else:
        verdict = "reject"
        confidence = 0.85

    confidence = min(confidence, 0.95)

    if verdict == "reject":
        report = f"{name} — rejected: {'; '.join(risks[:2]) if risks else 'failed all fundamental checks'}"
    elif verdict == "borderline":
        report = (
            f"{name} scores {score}/4 on fundamentals. "
            f"Positives: {', '.join(reasons) or 'none'}. "
            f"Concerns: {', '.join(risks) or 'none'}."
        )
    else:
        report = (
            f"{name} passes fundamentals with score {score}/4. "
            f"Strengths: {', '.join(reasons)}. "
            f"Minor risks: {', '.join(risks) or 'none'}."
        )

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": confidence,
        "report": report,
        "key_strengths": reasons,
        "key_risks": risks,
        "fcf_assessment": f"FCF positive years: {fcf_positive_years}/{min(len(fcf),5)}" if fcf else "no data",
        "score": score,
        "agent": "laxmi",
        # Detailed metrics — stored in DB, shown in dashboard detail panel
        "fcf_positive_years": fcf_positive_years,
        "roce_5yr_avg": roce,
        "debt_equity": de,
        "promoter_holding": ph,
        "promoter_pledge_pct": None,  # extracted by tara from shareholding_raw
        "inventory_days": wc["inventory_days"],
        "receivable_days": wc["receivable_days"],
        "payable_days": wc["payable_days"],
        "cash_conversion_cycle": (
            round(wc["inventory_days"] + wc["receivable_days"] - (wc["payable_days"] or 0), 1)
            if wc["inventory_days"] is not None and wc["receivable_days"] is not None
            else None
        ),
    }
