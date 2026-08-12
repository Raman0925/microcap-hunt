import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect DB to a fresh temp file; re-init schema."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_init_run_does_not_wipe_existing_companies():
    """init_run() must not delete already-analysed companies."""
    import state_tracker
    db.upsert_company({"symbol": "EXISTING", "name": "Existing Co", "verdict": "shortlist"})
    state_tracker.init_run(10)
    assert db.get_company("EXISTING") is not None, "init_run() wiped existing company"


def test_record_result_increments_total():
    import state_tracker
    before = db.get_stats()["total"]
    state_tracker.record_result({"symbol": "NEW", "name": "New Co", "verdict": "shortlist"})
    after = db.get_stats()["total"]
    assert after == before + 1


def test_agent_start_sets_analysing():
    import state_tracker
    state_tracker.agent_start("laxmi", "TEST", "Test Co")
    activity = db.get_agent_activity()
    assert activity.get("laxmi", {}).get("status") == "analysing"


def test_agent_done_sets_idle():
    import state_tracker
    state_tracker.agent_start("meera", "TEST", "Test Co")
    state_tracker.agent_done("meera", "pass")
    activity = db.get_agent_activity()
    assert activity.get("meera", {}).get("status") == "idle"


def test_record_result_upserts_on_duplicate():
    """Recording the same symbol twice updates rather than duplicates."""
    import state_tracker
    state_tracker.record_result({"symbol": "DUP", "verdict": "reject"})
    state_tracker.record_result({"symbol": "DUP", "verdict": "shortlist"})
    companies = db.get_all_companies()
    dups = [c for c in companies if c["symbol"] == "DUP"]
    assert len(dups) == 1
    assert dups[0]["verdict"] == "shortlist"
