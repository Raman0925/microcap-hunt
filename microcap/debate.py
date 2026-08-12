"""
debate.py — Debate and voting logic for Laxmi, Meera, and Tara (rule-based, no API key needed).

Aggregates the three agent verdicts using a weighted score and produces a final verdict.
Laxmi (fundamentals) carries the most weight.
"""

import logging

logger = logging.getLogger(__name__)

VERDICT_SCORES = {"reject": -1, "borderline": 0, "pass": 1}

# Laxmi weight is double (fundamentals matter most)
WEIGHTS = {"laxmi": 2.0, "meera": 1.0, "tara": 1.5}


def _tally_votes(laxmi: dict, meera: dict, tara: dict) -> dict:
    verdicts = [laxmi.get("verdict"), meera.get("verdict"), tara.get("verdict")]
    rejects = verdicts.count("reject")
    passes = verdicts.count("pass")
    borderlines = verdicts.count("borderline")

    weighted_score = (
        VERDICT_SCORES.get(laxmi.get("verdict", "borderline"), 0) * laxmi.get("confidence", 0.5) * WEIGHTS["laxmi"]
        + VERDICT_SCORES.get(meera.get("verdict", "borderline"), 0) * meera.get("confidence", 0.5) * WEIGHTS["meera"]
        + VERDICT_SCORES.get(tara.get("verdict", "borderline"), 0) * tara.get("confidence", 0.5) * WEIGHTS["tara"]
    )
    max_possible = WEIGHTS["laxmi"] + WEIGHTS["meera"] + WEIGHTS["tara"]

    return {
        "rejects": rejects,
        "passes": passes,
        "borderlines": borderlines,
        "weighted_score": round(weighted_score, 3),
        "normalised_score": round(weighted_score / max_possible, 3),
    }


def debate(laxmi: dict, meera: dict, tara: dict) -> dict:
    """
    Aggregate three agent verdicts and return a final verdict dict.

    Returns:
        {
            "symbol": str,
            "name": str,
            "final_verdict": "reject" | "borderline" | "shortlist",
            "confidence": float,
            "report": str,
            "debated": bool,
            "vote_tally": dict,
        }
    """
    symbol = laxmi.get("symbol", "UNKNOWN")
    name = laxmi.get("name", symbol)
    tally = _tally_votes(laxmi, meera, tara)

    logger.info(
        f"Debate tally for {symbol}: "
        f"passes={tally['passes']}, rejects={tally['rejects']}, "
        f"borderlines={tally['borderlines']}, score={tally['weighted_score']}"
    )

    # Hard stops — Laxmi or Tara governance reject overrides everything
    laxmi_rejects = laxmi.get("verdict") == "reject" and laxmi.get("confidence", 0) >= 0.8
    tara_governance_reject = (
        tara.get("verdict") == "reject" and tara.get("governance_signal") == "red_flag"
    )
    all_reject = tally["rejects"] == 3

    if all_reject or laxmi_rejects or tara_governance_reject:
        if tara_governance_reject:
            reason = tara.get("report", f"{name} — rejected: governance red flag")
        elif laxmi_rejects:
            reason = laxmi.get("report", f"{name} — rejected: fundamentals failed")
        else:
            reason = laxmi.get("report") or f"{name} — rejected by all three analysts"
        return {
            "symbol": symbol,
            "name": name,
            "final_verdict": "reject",
            "confidence": 0.90,
            "report": reason,
            "debated": False,
            "vote_tally": tally,
        }

    # Unanimous pass
    if tally["passes"] == 3:
        combined = (
            f"<b>SHORTLISTED — Unanimous Pass</b>\n\n"
            f"<b>Fundamentals (Laxmi):</b> {laxmi.get('report', 'N/A')}\n\n"
            f"<b>Technical (Meera):</b> {meera.get('report', 'N/A')}\n\n"
            f"<b>Story (Tara):</b> {tara.get('report', 'N/A')}"
        )
        return {
            "symbol": symbol,
            "name": name,
            "final_verdict": "shortlist",
            "confidence": 0.88,
            "report": combined,
            "investment_thesis": f"{name} passes all three filters — solid fundamentals, good technicals, clean story.",
            "debated": False,
            "vote_tally": tally,
        }

    # Score-based decision for mixed cases
    norm = tally["normalised_score"]

    if norm >= 0.35:
        verdict = "shortlist"
        confidence = 0.55 + norm * 0.3
        report = (
            f"<b>SHORTLISTED</b>\n\n"
            f"<b>Fundamentals (Laxmi):</b> {laxmi.get('report', 'N/A')}\n\n"
            f"<b>Technical (Meera):</b> {meera.get('report', 'N/A')}\n\n"
            f"<b>Story (Tara):</b> {tara.get('report', 'N/A')}\n\n"
            f"Combined score: {norm:.2f}. "
            f"Passes: {tally['passes']}, Borderlines: {tally['borderlines']}, Rejects: {tally['rejects']}."
        )
        thesis = f"{name} meets the combined bar across fundamentals, technicals, and narrative."
    elif norm >= -0.1:
        verdict = "borderline"
        confidence = 0.45
        report = (
            f"{name} — borderline (score {norm:.2f}). "
            f"Laxmi: {laxmi.get('verdict')} | Meera: {meera.get('verdict')} | Tara: {tara.get('verdict')}. "
            f"Worth watching but not a buy yet."
        )
        thesis = f"{name} is worth monitoring — mixed signals across the three filters."
    else:
        verdict = "reject"
        confidence = 0.70
        report = (
            f"{name} — rejected (score {norm:.2f}). "
            f"Laxmi: {laxmi.get('verdict')} | Meera: {meera.get('verdict')} | Tara: {tara.get('verdict')}."
        )
        thesis = ""

    return {
        "symbol": symbol,
        "name": name,
        "final_verdict": verdict,
        "confidence": min(confidence, 0.95),
        "report": report,
        "investment_thesis": thesis,
        "suggested_entry": "",
        "watch_for": "",
        "vote_tally": tally,
        "debated": True,
    }
