"""
laxmi.py — Fundamental analysis: Mukherjea/Buffett/Graham/Greenblatt framework.

Weighted scorecard (max 10 pts):
  FCF Quality:           0-2 pts  (4+ positive years = 2, 2-3 = 1, else 0)
  ROCE Consistency:      0-2 pts  (>20% = 2, 12-20% = 1, else 0)
  Debt Safety:           0-1 pt   (<0.5 = 1, 0.5-1.0 = 0.5, >1.0 = 0)
  Promoter Skin-in-Game: 0-1 pt   (>50% = 1, 35-50% = 0.5, else 0)
  Revenue Consistency:   0-1 pt   (3+ of last 4 years growing = 1)
  Forensic 3Cs:          0-2 pts  (VETO power on red flags)
  Working Capital CCC:   0-1 pt   (<60d = 1, 60-120d = 0.5, >120d = 0)

Score >= 7 = pass, 4-6 = borderline, < 4 = reject.
Forensic VETO overrides score (verdict=reject, confidence=0.95).
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


def _row_values(rows: list, *labels: str) -> list[Optional[float]]:
    """Find first row matching any label keyword; return numeric values (skip first col)."""
    for row in rows:
        label = (list(row.values())[0] if row else "").lower()
        if any(lbl in label for lbl in labels):
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def _row_last(rows: list, *labels: str) -> Optional[float]:
    """Return most recent (first) non-None value from a matching row."""
    vals = _row_values(rows, *labels)
    clean = [v for v in vals if v is not None]
    return clean[0] if clean else None


def _extract_fcf_series(company: dict) -> list[Optional[float]]:
    """FCF or operating CF proxy from cash_flow table."""
    cf_rows = company.get("cash_flow", [])
    for label_set in [
        ["free cash", "fcf"],
        ["cash from operations", "cash from operating"],
        ["operating activities"],
    ]:
        vals = _row_values(cf_rows, *label_set)
        if vals:
            return vals
    # Generic fallback: any row with "operating"
    for row in cf_rows:
        label = (list(row.values())[0] if row else "").lower()
        if "operating" in label:
            return [_parse_number(v) for v in list(row.values())[1:]]
    return []


def _extract_operating_cf(company: dict) -> list[Optional[float]]:
    """Operating cash flow (OCF) for forensic CFO/Net-Profit ratio check."""
    cf_rows = company.get("cash_flow", [])
    for label_set in [
        ["cash from operations", "cash from operating"],
        ["operating activities"],
        ["net cash from operating"],
    ]:
        vals = _row_values(cf_rows, *label_set)
        if vals:
            return vals
    return _extract_fcf_series(company)


def _extract_net_profit_series(company: dict) -> list[Optional[float]]:
    pl_rows = company.get("profit_loss", [])
    cf_rows = company.get("cash_flow", [])
    vals = _row_values(pl_rows, "net profit", "pat", "profit after tax", "profit for the year")
    if vals:
        return vals
    return _row_values(cf_rows, "net profit", "pat")


def _extract_revenue_series(company: dict) -> list[Optional[float]]:
    pl_rows = company.get("profit_loss", [])
    return _row_values(pl_rows, "sales", "revenue from operations", "revenue")


def _extract_working_capital(company: dict) -> dict:
    bs_rows = company.get("balance_sheet", [])
    pl_rows = company.get("profit_loss", [])

    inventory = _row_last(bs_rows, "inventories", "inventory")
    receivables = _row_last(bs_rows, "trade receivable", "debtors", "receivable")
    payables = _row_last(bs_rows, "trade payable", "creditors", "payable")
    revenue = _row_last(pl_rows, "sales", "revenue from operations", "revenue")

    inv_days = recv_days = pay_days = None
    if revenue and revenue > 0:
        daily = revenue / 365
        if inventory is not None:
            inv_days = round(inventory / daily, 1)
        if receivables is not None:
            recv_days = round(receivables / daily, 1)
        if payables is not None:
            pay_days = round(payables / daily, 1)

    return {"inventory_days": inv_days, "receivable_days": recv_days, "payable_days": pay_days}


def _detect_promoter_pledge(shareholding_raw: str) -> Optional[float]:
    if not shareholding_raw:
        return None
    m = re.search(r"pledge[d]?\s*[:\-]?\s*(\d+\.?\d*)\s*%", shareholding_raw.lower())
    return float(m.group(1)) if m else None


def analyse(company: dict) -> dict:
    symbol = company.get("symbol", "UNKNOWN")
    name = company.get("name", symbol)
    about = (company.get("about") or "").lower()
    shareholding_raw = company.get("shareholding_raw") or ""

    score = 0.0
    strengths: list[str] = []
    risks: list[str] = []
    forensic_flags: list[str] = []
    red_flags: list[str] = []

    # ── 1. FCF Quality (2 pts) ──────────────────────────────────────────────
    fcf = _extract_fcf_series(company)
    fcf_positive_years: Optional[int] = None
    if fcf:
        recent = [v for v in fcf[:5] if v is not None]
        pos = sum(1 for v in recent if v > 0)
        fcf_positive_years = pos
        n = len(recent)
        if pos >= 4:
            score += 2
            strengths.append(f"FCF positive {pos}/{n} years — excellent cash generation")
        elif pos >= 2:
            score += 1
            strengths.append(f"FCF positive {pos}/{n} years — adequate")
        else:
            risks.append(f"FCF inconsistent — only {pos}/{n} years positive")
    else:
        risks.append("FCF data unavailable")

    # ── 2. ROCE Consistency (2 pts) — Greenblatt + Mukherjea ───────────────
    roce = _parse_number(company.get("roce"))
    if roce is not None:
        if roce > 20:
            score += 2
            strengths.append(f"ROCE {roce:.1f}% > 20% — exceptional capital efficiency")
        elif roce >= 12:
            score += 1
            strengths.append(f"ROCE {roce:.1f}% (adequate)")
        else:
            risks.append(f"Low ROCE: {roce:.1f}% — poor capital efficiency")
    else:
        risks.append("ROCE not available")

    # ── 3. Debt Safety (1 pt) — Graham ─────────────────────────────────────
    de = _parse_number(company.get("debt_to_equity"))
    if de is not None:
        if de < 0.5:
            score += 1
            strengths.append(f"Low D/E: {de:.2f} — fortress balance sheet")
        elif de <= 1.0:
            score += 0.5
            risks.append(f"Moderate D/E: {de:.2f}")
        else:
            risks.append(f"High D/E: {de:.2f} — elevated leverage risk")
    else:
        risks.append("D/E ratio not available")

    # ── 4. Promoter Skin-in-Game (1 pt) ────────────────────────────────────
    ph = _parse_number(company.get("promoter_holding"))
    pledge_pct = _detect_promoter_pledge(shareholding_raw)

    if ph is not None:
        if ph > 50:
            score += 1
            strengths.append(f"High promoter holding: {ph:.1f}%")
        elif ph >= 35:
            score += 0.5
            risks.append(f"Moderate promoter holding: {ph:.1f}%")
        else:
            risks.append(f"Low promoter holding: {ph:.1f}% — low skin in the game")
    else:
        risks.append("Promoter holding data not available")

    # ── 5. Revenue Consistency (1 pt) — Mukherjea/Bakshi ──────────────────
    revenue = _extract_revenue_series(company)
    revenue_growth_years = 0
    if revenue:
        valid = [v for v in revenue[:5] if v is not None and v > 0]
        total_pairs = len(valid) - 1
        for i in range(total_pairs):
            if valid[i] > valid[i + 1]:  # recent-first ordering → current > prior = growth
                revenue_growth_years += 1
        if total_pairs > 0 and revenue_growth_years >= 3:
            score += 1
            strengths.append(f"Revenue grew {revenue_growth_years}/{total_pairs} years consistently")
        elif revenue_growth_years > 0:
            risks.append(f"Revenue growth inconsistent ({revenue_growth_years}/{total_pairs} years)")
        else:
            risks.append("Revenue declining or flat")
    else:
        risks.append("Revenue data unavailable")

    # ── 6. Forensic Accounting — Mukherjea 3Cs (2 pts, VETO) ──────────────
    # Only award "clean" credits when there's enough text to actually verify.
    has_about = len(about) >= 50

    forensic_score = 0.0
    forensic_veto = False

    # CFO / Net-Profit ratio
    ocf_series = _extract_operating_cf(company)
    np_series = _extract_net_profit_series(company)
    cfo_to_ebitda: Optional[float] = None

    if ocf_series and np_series:
        streak = 0
        ratios: list[float] = []
        for ocf_v, np_v in zip(ocf_series[:5], np_series[:5]):
            if ocf_v is not None and np_v is not None and np_v > 0:
                r = ocf_v / np_v
                ratios.append(r)
                if r < 0.3:
                    streak += 1
                else:
                    streak = 0
        if ratios:
            cfo_to_ebitda = round(ratios[0], 2)
        if streak >= 2:
            forensic_flags.append("CFO << Net Profit for 2+ consecutive years — earnings quality concern")
            red_flags.append("Forensic VETO: CFO/Net Profit < 0.3x for 2+ years")
            forensic_veto = True
        else:
            forensic_score += 0.5

    # Related-party transaction check (requires meaningful about text)
    if has_about:
        rpt_kws = ["related party", "group company loan", "inter-company", "related-party"]
        rpt_count = sum(about.count(kw) for kw in rpt_kws)
        if rpt_count > 5:
            forensic_flags.append(f"High related-party mentions in description ({rpt_count})")
        else:
            forensic_score += 0.5

    # Auditor signals
    if has_about:
        auditor_red = ["auditor resigned", "qualified opinion", "emphasis of matter", "going concern"]
        if any(kw in about for kw in auditor_red):
            forensic_flags.append("Auditor qualification/resignation signals detected")
            red_flags.append("Forensic VETO: Auditor red flag")
            forensic_veto = True
        else:
            forensic_score += 0.5

    # Inventory spike check
    bs_rows = company.get("balance_sheet", [])
    inv_vals = _row_values(bs_rows, "inventories", "inventory")
    rev_vals = _extract_revenue_series(company)
    if len(inv_vals) >= 2 and len(rev_vals) >= 2:
        inv_clean = [v for v in inv_vals[:2] if v is not None]
        rev_clean = [v for v in rev_vals[:2] if v is not None]
        if len(inv_clean) == 2 and len(rev_clean) == 2 and inv_clean[1] > 0 and rev_clean[1] > 0:
            inv_growth = inv_clean[0] / inv_clean[1]
            rev_growth = rev_clean[0] / rev_clean[1]
            if inv_growth >= 2 * rev_growth and inv_growth > 1.2:
                forensic_flags.append("Inventory growing 2x+ faster than revenue — possible channel stuffing")
            else:
                forensic_score += 0.5

    forensic_score = min(forensic_score, 2.0)
    score += forensic_score

    # ── 7. Working Capital Health — CCC (1 pt) ─────────────────────────────
    wc = _extract_working_capital(company)
    inv_d, recv_d, pay_d = wc["inventory_days"], wc["receivable_days"], wc["payable_days"]
    ccc: Optional[float] = None

    if inv_d is not None and recv_d is not None:
        ccc = round(inv_d + recv_d - (pay_d or 0), 1)
        if ccc < 60:
            score += 1
            strengths.append(f"Excellent CCC: {ccc:.0f} days")
        elif ccc <= 120:
            score += 0.5
            risks.append(f"Moderate CCC: {ccc:.0f} days")
        else:
            risks.append(f"Poor CCC: {ccc:.0f} days — working capital strain")
    # No data → 0 pts (can't claim clean)

    # ── VETO check ──────────────────────────────────────────────────────────
    score = round(score, 1)

    if forensic_veto:
        return {
            "symbol": symbol,
            "name": name,
            "verdict": "reject",
            "confidence": 0.95,
            "report": f"{name} — FORENSIC VETO: {'; '.join(forensic_flags[:2])}",
            "score": score,
            "key_strengths": strengths,
            "key_risks": risks + forensic_flags,
            "red_flags": red_flags,
            "fcf_positive_years": fcf_positive_years,
            "roce_5yr_avg": roce,
            "debt_equity": de,
            "promoter_holding": ph,
            "promoter_pledge_pct": pledge_pct,
            "inventory_days": inv_d,
            "receivable_days": recv_d,
            "payable_days": pay_d,
            "cash_conversion_cycle": ccc,
            "revenue_growth_years": revenue_growth_years,
            "cfo_to_ebitda": cfo_to_ebitda,
            "forensic_flags": forensic_flags,
            "owner_earnings": None,
            "agent": "laxmi",
        }

    # ── Verdict ─────────────────────────────────────────────────────────────
    if score >= 7:
        verdict = "pass"
        confidence = min(0.50 + (score - 7) * 0.10, 0.95)
    elif score >= 4:
        verdict = "borderline"
        confidence = 0.35 + (score - 4) * 0.05
    else:
        verdict = "reject"
        confidence = max(0.85, 0.95 - score * 0.02)

    # Owner earnings: net profit + depreciation - capex (proxy: just net profit if dep/capex unavailable)
    np_series = _extract_net_profit_series(company)
    owner_earnings: Optional[float] = None
    if np_series:
        latest = next((v for v in np_series if v is not None), None)
        if latest is not None:
            owner_earnings = round(latest, 1)

    if verdict == "reject":
        report = (
            f"{name} — rejected (score {score}/10): "
            f"{'; '.join((risks + red_flags)[:2]) or 'failed fundamental checks'}"
        )
    elif verdict == "borderline":
        report = (
            f"{name} scores {score}/10 on fundamentals. "
            f"Strengths: {', '.join(strengths[:2]) or 'none'}. "
            f"Concerns: {', '.join(risks[:2]) or 'none'}."
        )
    else:
        report = (
            f"{name} passes fundamentals (score {score}/10). "
            f"Strengths: {', '.join(strengths[:3])}. "
            f"Risks: {', '.join(risks[:2]) or 'none'}."
        )

    return {
        "symbol": symbol,
        "name": name,
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "report": report,
        "score": score,
        "key_strengths": strengths,
        "key_risks": risks,
        "red_flags": red_flags,
        "fcf_positive_years": fcf_positive_years,
        "roce_5yr_avg": roce,
        "debt_equity": de,
        "promoter_holding": ph,
        "promoter_pledge_pct": pledge_pct,
        "inventory_days": inv_d,
        "receivable_days": recv_d,
        "payable_days": pay_d,
        "cash_conversion_cycle": ccc,
        "revenue_growth_years": revenue_growth_years,
        "cfo_to_ebitda": cfo_to_ebitda,
        "forensic_flags": forensic_flags,
        "owner_earnings": owner_earnings,
        "agent": "laxmi",
    }
