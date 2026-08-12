"""
db.py — SQLite persistence layer for Microcap Hunt.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "microcap.db"
_lock = threading.Lock()

# Columns stored as JSON that should be decoded back into lists on read.
_JSON_LIST_FIELDS = (
    "red_flags", "positives", "debate_reasoning",
    "taleb_signals", "optionality_signals", "key_strengths", "key_risks",
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _add_column_if_missing(conn, table, col, col_type):
    existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")


# New columns added by the upgraded investment framework.
_EXTRA_COLUMNS = [
    ("debate_reasoning", "TEXT"),
    ("taleb_signals", "TEXT"),
    ("smile_score", "REAL"),
    ("optionality_signals", "TEXT"),
    ("contrarian_angle", "TEXT"),
    ("revenue_growth_pct", "REAL"),
    ("profit_growth_pct", "REAL"),
    ("pe_ratio", "REAL"),
    ("cfo_to_ebitda", "REAL"),
    ("owner_earnings", "REAL"),
    ("revenue_growth_years", "INTEGER"),
    ("key_strengths", "TEXT"),
    ("key_risks", "TEXT"),
    ("market_cap", "TEXT"),
]


def init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS companies (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                market_cap_cr REAL,
                verdict TEXT,
                confidence REAL,
                laxmi_verdict TEXT,
                meera_verdict TEXT,
                tara_verdict TEXT,
                laxmi_score REAL,
                meera_score REAL,
                tara_score REAL,
                report TEXT,
                investment_thesis TEXT,
                screener_url TEXT,
                fcf_positive_years INTEGER,
                roce_5yr_avg REAL,
                debt_equity REAL,
                promoter_holding_pct REAL,
                promoter_pledging_pct REAL,
                inventory_days REAL,
                receivable_days REAL,
                cash_conversion_cycle REAL,
                optionality_score REAL,
                red_flags TEXT,
                positives TEXT,
                analyzed_at REAL,
                updated_at REAL
            );

            CREATE TABLE IF NOT EXISTS agent_activity (
                agent_name TEXT PRIMARY KEY,
                status TEXT DEFAULT 'idle',
                current_symbol TEXT,
                current_company TEXT,
                last_verdict TEXT,
                count INTEGER DEFAULT 0,
                updated_at REAL
            );

            CREATE TABLE IF NOT EXISTS run_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_companies INTEGER,
                analysed INTEGER,
                shortlisted INTEGER,
                borderline INTEGER,
                rejected INTEGER,
                run_started REAL,
                last_updated REAL
            );
        """)

        # Add framework-upgrade columns if they don't already exist.
        for col, col_type in _EXTRA_COLUMNS:
            _add_column_if_missing(conn, "companies", col, col_type)


def upsert_company(result: dict):
    """Insert or update a company from an analysis result dict."""
    now = time.time()
    sym = result.get("symbol", "")
    if not sym:
        return

    # Handle laxmi sub-dict
    laxmi = result.get("laxmi") or {}
    meera = result.get("meera") or {}
    tara = result.get("tara") or {}
    optionality = result.get("optionality") or {}

    # Verdict field: accept 'final_verdict' or 'verdict'
    verdict = result.get("verdict") or result.get("final_verdict") or "reject"

    # analyzed_at: accept timestamp (float from dashboard_data) or ISO string (from results/)
    analyzed_at = result.get("analyzed_at") or result.get("timestamp")
    if isinstance(analyzed_at, str):
        try:
            import datetime
            analyzed_at = datetime.datetime.fromisoformat(
                analyzed_at.replace("Z", "+00:00")
            ).timestamp()
        except Exception:
            analyzed_at = now

    red_flags = result.get("red_flags")
    positives = result.get("positives")

    def _jd(val):
        """json.dumps lists/dicts, pass through scalars/None."""
        if isinstance(val, (list, dict)):
            return json.dumps(val)
        return val

    # ── Upgraded-framework fields ──────────────────────────────────────────
    debate_reasoning = result.get("debate_reasoning") or result.get("reasoning_chain")
    taleb_signals = tara.get("taleb_signals") or result.get("taleb_signals")
    smile_score = tara.get("smile_score")
    if smile_score is None:
        smile_score = result.get("smile_score")
    optionality_signals = meera.get("optionality_signals") or result.get("optionality_signals")
    contrarian_angle = tara.get("contrarian_angle")
    revenue_growth_pct = meera.get("revenue_growth_pct")
    profit_growth_pct = meera.get("profit_growth_pct")
    pe_ratio = meera.get("pe_ratio")
    if pe_ratio is None:
        pe_ratio = result.get("pe_ratio")
    cfo_to_ebitda = laxmi.get("cfo_to_ebitda")
    owner_earnings = laxmi.get("owner_earnings")
    revenue_growth_years = laxmi.get("revenue_growth_years")
    key_strengths = laxmi.get("key_strengths") or result.get("key_strengths")
    key_risks = laxmi.get("key_risks") or result.get("key_risks")
    market_cap = result.get("market_cap", "")

    with _lock:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO companies (
                    symbol, name, sector, market_cap_cr, verdict, confidence,
                    laxmi_verdict, meera_verdict, tara_verdict,
                    laxmi_score, meera_score, tara_score,
                    report, investment_thesis, screener_url,
                    fcf_positive_years, roce_5yr_avg, debt_equity,
                    promoter_holding_pct, promoter_pledging_pct,
                    inventory_days, receivable_days, cash_conversion_cycle,
                    optionality_score, red_flags, positives,
                    debate_reasoning, taleb_signals, smile_score,
                    optionality_signals, contrarian_angle,
                    revenue_growth_pct, profit_growth_pct, pe_ratio,
                    cfo_to_ebitda, owner_earnings, revenue_growth_years,
                    key_strengths, key_risks, market_cap,
                    analyzed_at, updated_at
                ) VALUES (
                    :symbol, :name, :sector, :market_cap_cr, :verdict, :confidence,
                    :laxmi_verdict, :meera_verdict, :tara_verdict,
                    :laxmi_score, :meera_score, :tara_score,
                    :report, :investment_thesis, :screener_url,
                    :fcf_positive_years, :roce_5yr_avg, :debt_equity,
                    :promoter_holding_pct, :promoter_pledging_pct,
                    :inventory_days, :receivable_days, :cash_conversion_cycle,
                    :optionality_score, :red_flags, :positives,
                    :debate_reasoning, :taleb_signals, :smile_score,
                    :optionality_signals, :contrarian_angle,
                    :revenue_growth_pct, :profit_growth_pct, :pe_ratio,
                    :cfo_to_ebitda, :owner_earnings, :revenue_growth_years,
                    :key_strengths, :key_risks, :market_cap,
                    :analyzed_at, :updated_at
                )
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    sector=excluded.sector,
                    market_cap_cr=excluded.market_cap_cr,
                    verdict=excluded.verdict,
                    confidence=excluded.confidence,
                    laxmi_verdict=excluded.laxmi_verdict,
                    meera_verdict=excluded.meera_verdict,
                    tara_verdict=excluded.tara_verdict,
                    laxmi_score=excluded.laxmi_score,
                    meera_score=excluded.meera_score,
                    tara_score=excluded.tara_score,
                    report=excluded.report,
                    investment_thesis=excluded.investment_thesis,
                    screener_url=excluded.screener_url,
                    fcf_positive_years=excluded.fcf_positive_years,
                    roce_5yr_avg=excluded.roce_5yr_avg,
                    debt_equity=excluded.debt_equity,
                    promoter_holding_pct=excluded.promoter_holding_pct,
                    promoter_pledging_pct=excluded.promoter_pledging_pct,
                    inventory_days=excluded.inventory_days,
                    receivable_days=excluded.receivable_days,
                    cash_conversion_cycle=excluded.cash_conversion_cycle,
                    optionality_score=excluded.optionality_score,
                    red_flags=excluded.red_flags,
                    positives=excluded.positives,
                    debate_reasoning=excluded.debate_reasoning,
                    taleb_signals=excluded.taleb_signals,
                    smile_score=excluded.smile_score,
                    optionality_signals=excluded.optionality_signals,
                    contrarian_angle=excluded.contrarian_angle,
                    revenue_growth_pct=excluded.revenue_growth_pct,
                    profit_growth_pct=excluded.profit_growth_pct,
                    pe_ratio=excluded.pe_ratio,
                    cfo_to_ebitda=excluded.cfo_to_ebitda,
                    owner_earnings=excluded.owner_earnings,
                    revenue_growth_years=excluded.revenue_growth_years,
                    key_strengths=excluded.key_strengths,
                    key_risks=excluded.key_risks,
                    market_cap=excluded.market_cap,
                    analyzed_at=excluded.analyzed_at,
                    updated_at=excluded.updated_at
                """,
                {
                    "symbol": sym,
                    "name": result.get("name", sym),
                    "sector": result.get("sector", ""),
                    "market_cap_cr": result.get("market_cap_cr"),
                    "verdict": verdict,
                    "confidence": result.get("confidence"),
                    "laxmi_verdict": laxmi.get("verdict") or result.get("laxmi_verdict", ""),
                    "meera_verdict": meera.get("verdict") or result.get("meera_verdict", ""),
                    "tara_verdict": tara.get("verdict") or result.get("tara_verdict", ""),
                    "laxmi_score": laxmi.get("score"),
                    "meera_score": meera.get("score"),
                    "tara_score": tara.get("score"),
                    "report": result.get("report", ""),
                    "investment_thesis": result.get("investment_thesis", ""),
                    "screener_url": result.get("screener_url", f"https://www.screener.in/company/{sym}/"),
                    "fcf_positive_years": _parse_fcf_years(laxmi.get("fcf_positive_years")),
                    "roce_5yr_avg": laxmi.get("roce_5yr_avg"),
                    "debt_equity": laxmi.get("debt_equity"),
                    "promoter_holding_pct": laxmi.get("promoter_holding"),
                    "promoter_pledging_pct": laxmi.get("promoter_pledge_pct"),
                    "inventory_days": _list_last(laxmi.get("inventory_days")),
                    "receivable_days": _list_last(laxmi.get("receivable_days")),
                    "cash_conversion_cycle": laxmi.get("cash_conversion_cycle"),
                    "optionality_score": optionality.get("score"),
                    "red_flags": json.dumps(red_flags) if red_flags is not None else None,
                    "positives": json.dumps(positives) if positives is not None else None,
                    "debate_reasoning": _jd(debate_reasoning),
                    "taleb_signals": _jd(taleb_signals),
                    "smile_score": smile_score,
                    "optionality_signals": _jd(optionality_signals),
                    "contrarian_angle": contrarian_angle,
                    "revenue_growth_pct": revenue_growth_pct,
                    "profit_growth_pct": profit_growth_pct,
                    "pe_ratio": pe_ratio,
                    "cfo_to_ebitda": cfo_to_ebitda,
                    "owner_earnings": owner_earnings,
                    "revenue_growth_years": revenue_growth_years,
                    "key_strengths": _jd(key_strengths),
                    "key_risks": _jd(key_risks),
                    "market_cap": market_cap,
                    "analyzed_at": analyzed_at,
                    "updated_at": now,
                },
            )


def _parse_fcf_years(val) -> int | None:
    """Parse '4/5' or integer into an integer."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str) and "/" in val:
        try:
            return int(val.split("/")[0])
        except ValueError:
            pass
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _list_last(val) -> float | None:
    """Return last element of a list, or val itself if scalar."""
    if isinstance(val, list):
        return val[-1] if val else None
    return val


# Maps a normalized verdict (as used by the API) to the raw verdict strings
# stored in the DB, so the companies list can be filtered per dashboard tab.
_VERDICT_DB_MAP = {
    "shortlisted": ("shortlist", "shortlisted"),
    "rejected": ("reject", "rejected", "auto_rejected_fraud_veto"),
    "borderline": ("borderline",),
    "pass": ("pass",),
}


def get_all_companies(limit=None, offset=None, verdict=None) -> list[dict]:
    sql = "SELECT * FROM companies"
    params: list = []
    if verdict and verdict in _VERDICT_DB_MAP:
        vals = _VERDICT_DB_MAP[verdict]
        placeholders = ",".join("?" * len(vals))
        sql += f" WHERE verdict IN ({placeholders})"
        params.extend(vals)
    sql += " ORDER BY analyzed_at DESC NULLS LAST"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
        if offset:
            sql += " OFFSET ?"
            params.append(offset)
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        for field in _JSON_LIST_FIELDS:
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        result.append(d)
    return result


def get_companies_count(verdict=None) -> int:
    sql = "SELECT COUNT(*) AS n FROM companies"
    params: list = []
    if verdict and verdict in _VERDICT_DB_MAP:
        vals = _VERDICT_DB_MAP[verdict]
        placeholders = ",".join("?" * len(vals))
        sql += f" WHERE verdict IN ({placeholders})"
        params.extend(vals)
    with _connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return row["n"] if row else 0


def get_company(symbol: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM companies WHERE symbol = ?", (symbol.upper(),)
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    for field in _JSON_LIST_FIELDS:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except Exception:
                pass
    return d


def get_stats() -> dict:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN verdict='shortlist' OR verdict='shortlisted' THEN 1 ELSE 0 END) AS shortlisted,
                SUM(CASE WHEN verdict='borderline' THEN 1 ELSE 0 END) AS borderline,
                SUM(CASE WHEN verdict='reject' OR verdict='rejected' THEN 1 ELSE 0 END) AS rejected
            FROM companies
            """
        ).fetchone()
    return {
        "total": row["total"] or 0,
        "shortlisted": row["shortlisted"] or 0,
        "borderline": row["borderline"] or 0,
        "rejected": row["rejected"] or 0,
    }


def set_agent_status(agent_name: str, status: str, symbol: str = None, company: str = None):
    now = time.time()
    with _lock:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_activity (agent_name, status, current_symbol, current_company, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(agent_name) DO UPDATE SET
                    status=excluded.status,
                    current_symbol=excluded.current_symbol,
                    current_company=excluded.current_company,
                    updated_at=excluded.updated_at
                """,
                (agent_name, status, symbol, company, now),
            )


def increment_agent_count(agent_name: str, verdict: str):
    now = time.time()
    with _lock:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_activity (agent_name, status, last_verdict, count, updated_at)
                VALUES (?, 'idle', ?, 1, ?)
                ON CONFLICT(agent_name) DO UPDATE SET
                    status='idle',
                    last_verdict=excluded.last_verdict,
                    count=count + 1,
                    updated_at=excluded.updated_at
                """,
                (agent_name, verdict, now),
            )


def get_agent_activity() -> dict:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM agent_activity").fetchall()
    return {row["agent_name"]: dict(row) for row in rows}


def get_run_stats() -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM run_stats ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def upsert_run_stats(total: int, run_started: float = None):
    now = time.time()
    stats = get_stats()
    with _lock:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO run_stats
                    (total_companies, analysed, shortlisted, borderline, rejected, run_started, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    total,
                    stats["total"],
                    stats["shortlisted"],
                    stats["borderline"],
                    stats["rejected"],
                    run_started or now,
                    now,
                ),
            )
