"""
reporter.py — Formats and sends analysis reports to Telegram.

Handles both individual company reports and batch summaries.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
CHAT_ID = 8495865824
MAX_MESSAGE_LENGTH = 4096  # Telegram limit


def _get_token() -> Optional[str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram reporting disabled")
    return token


def _send_telegram(text: str, token: str, parse_mode: str = "HTML") -> bool:
    """Send a message to Telegram. Splits long messages automatically."""
    url = TELEGRAM_API.format(token=token)

    # Split if too long
    chunks = []
    while len(text) > MAX_MESSAGE_LENGTH:
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    chunks.append(text)

    success = True
    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": CHAT_ID,
                    "text": chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if not resp.ok:
                logger.error(f"Telegram send failed: {resp.status_code} {resp.text[:200]}")
                success = False
        except Exception as e:
            logger.error(f"Telegram send exception: {e}")
            success = False
    return success


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_company_report(result: dict) -> str:
    """Format a single company debate result into a Telegram-ready HTML message."""
    name = _escape_html(result.get("name", result.get("symbol", "Unknown")))
    symbol = result.get("symbol", "")
    verdict = result.get("final_verdict", "borderline")
    confidence = result.get("confidence", 0)
    report = _escape_html(result.get("report", "No report available"))
    screener_url = f"https://www.screener.in/company/{symbol}/"

    verdict_emoji = {"reject": "❌", "borderline": "⚠️", "shortlist": "✅"}.get(verdict, "❓")
    verdict_label = verdict.upper()

    lines = [
        f"{verdict_emoji} <b>{name}</b> ({symbol})",
        f"<b>Verdict:</b> {verdict_label} | <b>Confidence:</b> {confidence:.0%}",
        "",
        report,
    ]

    if verdict == "shortlist":
        thesis = result.get("investment_thesis", "")
        entry = result.get("suggested_entry", "")
        watch = result.get("watch_for", "")
        if thesis:
            lines.append(f"\n📌 <b>Thesis:</b> {_escape_html(thesis)}")
        if entry:
            lines.append(f"🎯 <b>Entry:</b> {_escape_html(entry)}")
        if watch:
            lines.append(f"👁 <b>Watch:</b> {_escape_html(watch)}")

        tally = result.get("vote_tally", {})
        if tally:
            lines.append(
                f"\n🗳 Votes: Laxmi/Meera/Tara — "
                f"Pass: {tally.get('passes', 0)}, "
                f"Borderline: {tally.get('borderlines', 0)}, "
                f"Reject: {tally.get('rejects', 0)}"
            )

    lines.append(f"\n🔗 <a href='{screener_url}'>Screener.in</a>")

    return "\n".join(lines)


def format_batch_summary(results: list[dict], batch_num: int) -> str:
    """Format a summary message for a completed batch."""
    total = len(results)
    shortlisted = [r for r in results if r.get("final_verdict") == "shortlist"]
    borderline = [r for r in results if r.get("final_verdict") == "borderline"]
    rejected = [r for r in results if r.get("final_verdict") == "reject"]

    lines = [
        f"📊 <b>Microcap Hunt — Batch {batch_num} Summary</b>",
        f"Analysed: {total} companies",
        f"✅ Shortlisted: {len(shortlisted)}",
        f"⚠️ Borderline: {len(borderline)}",
        f"❌ Rejected: {len(rejected)}",
        "",
    ]

    if shortlisted:
        lines.append("<b>🌟 Shortlisted Companies:</b>")
        for r in shortlisted:
            name = _escape_html(r.get("name", r.get("symbol", "")))
            symbol = r.get("symbol", "")
            conf = r.get("confidence", 0)
            thesis = _escape_html(r.get("investment_thesis", ""))[:100]
            lines.append(f"• <b>{name}</b> ({symbol}) — {conf:.0%} confidence")
            if thesis:
                lines.append(f"  <i>{thesis}</i>")

    if borderline:
        lines.append("\n<b>⚠️ Worth Watching:</b>")
        for r in borderline[:5]:  # Top 5 borderline
            name = _escape_html(r.get("name", r.get("symbol", "")))
            symbol = r.get("symbol", "")
            lines.append(f"• {name} ({symbol})")

    return "\n".join(lines)


def send_company_report(result: dict) -> bool:
    """Send a single company report to Telegram. Returns True if sent."""
    token = _get_token()
    if not token:
        logger.info(f"[DRY RUN] Would send report for {result.get('symbol')}: {result.get('final_verdict')}")
        return False

    # Only send to Telegram for shortlisted and borderline — suppress rejects (too noisy)
    verdict = result.get("final_verdict", "")
    if verdict == "reject":
        # Log reject but don't spam Telegram
        logger.info(f"REJECT: {result.get('report', '')}")
        return True

    message = format_company_report(result)
    return _send_telegram(message, token)


def send_batch_summary(results: list[dict], batch_num: int) -> bool:
    """Send batch summary to Telegram."""
    token = _get_token()
    if not token:
        logger.info(f"[DRY RUN] Would send batch {batch_num} summary ({len(results)} companies)")
        return False

    message = format_batch_summary(results, batch_num)
    return _send_telegram(message, token)


def send_startup_message(total_companies: int) -> bool:
    """Notify Telegram that a new hunt session has started."""
    token = _get_token()
    if not token:
        return False
    msg = (
        f"🚀 <b>Project Microcap Hunt Started</b>\n"
        f"Scanning {total_companies} Indian microcap companies...\n"
        f"Agents: Laxmi (fundamentals) + Meera (technical) + Tara (story)"
    )
    return _send_telegram(msg, token)


def send_error_alert(error_msg: str) -> bool:
    """Send an error notification to Telegram."""
    token = _get_token()
    if not token:
        return False
    msg = f"⚠️ <b>Microcap Hunt Error</b>\n{_escape_html(error_msg[:500])}"
    return _send_telegram(msg, token)
