"""
state_tracker.py — Writes live state for the dashboard.

Tracks agent activity, company verdicts, and run progress.
Now backed by SQLite via db.py.
"""

import logging
import time

import db

logger = logging.getLogger(__name__)

db.init_db()


def init_run(total_companies: int):
    db.upsert_run_stats(total=total_companies, run_started=time.time())
    for agent_name in ("laxmi", "meera", "tara"):
        db.set_agent_status(agent_name, "waiting")


def agent_start(agent_name: str, symbol: str, company_name: str):
    db.set_agent_status(agent_name, "analysing", symbol=symbol, company=company_name)


def agent_done(agent_name: str, verdict: str):
    db.increment_agent_count(agent_name, verdict)


def record_result(result: dict):
    db.upsert_company(result)
