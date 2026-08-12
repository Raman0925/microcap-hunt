import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect all DB operations to a fresh temp file for each test."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_upsert_then_get_returns_same_data():
    db.upsert_company({"symbol": "TEST", "name": "Test Co", "verdict": "shortlist"})
    result = db.get_company("TEST")
    assert result is not None
    assert result["symbol"] == "TEST"
    assert result["name"] == "Test Co"


def test_upsert_twice_only_one_record():
    db.upsert_company({"symbol": "TEST", "name": "Test Co v1", "verdict": "reject"})
    db.upsert_company({"symbol": "TEST", "name": "Test Co v2", "verdict": "shortlist"})
    companies = db.get_all_companies()
    matches = [c for c in companies if c["symbol"] == "TEST"]
    assert len(matches) == 1
    assert matches[0]["verdict"] == "shortlist"  # updated value


def test_get_stats_correct_counts():
    db.upsert_company({"symbol": "A", "verdict": "shortlist"})
    db.upsert_company({"symbol": "B", "verdict": "reject"})
    db.upsert_company({"symbol": "C", "verdict": "borderline"})
    stats = db.get_stats()
    assert stats["total"] == 3
    assert stats["shortlisted"] == 1
    assert stats["rejected"] == 1
    assert stats["borderline"] == 1


def test_set_agent_status_then_get_activity():
    db.set_agent_status("laxmi", "analysing", "TESTCO", "Test Company")
    activity = db.get_agent_activity()
    assert "laxmi" in activity
    assert activity["laxmi"]["status"] == "analysing"
    assert activity["laxmi"]["current_symbol"] == "TESTCO"


def test_get_all_companies_returns_list():
    db.upsert_company({"symbol": "X", "verdict": "pass"})
    db.upsert_company({"symbol": "Y", "verdict": "reject"})
    result = db.get_all_companies()
    assert isinstance(result, list)
    assert len(result) == 2


def test_upsert_none_values_no_crash():
    """None values should not cause SQLite constraint errors."""
    db.upsert_company({
        "symbol": "NONE_TEST",
        "name": None,
        "verdict": None,
        "confidence": None,
        "market_cap_cr": None,
    })
    result = db.get_company("NONE_TEST")
    assert result is not None


def test_get_company_not_found_returns_none():
    assert db.get_company("DOESNOTEXIST") is None


def test_get_stats_empty_db():
    stats = db.get_stats()
    assert stats["total"] == 0
    assert stats["shortlisted"] == 0
