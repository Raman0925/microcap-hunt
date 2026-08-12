import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import fetcher


def test_parse_number_currency_and_commas():
    """₹19,500 Cr → 19500.0 after stripping currency symbols."""
    result = fetcher._parse_number("₹19,500 Cr")
    assert result == 19500.0


def test_parse_number_plain():
    assert fetcher._parse_number("1234.56") == 1234.56


def test_parse_number_empty_returns_none():
    assert fetcher._parse_number("") is None
    assert fetcher._parse_number(None) is None


def test_parse_number_invalid_returns_none():
    assert fetcher._parse_number("N/A") is None


def test_load_progress_returns_default_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "PROGRESS_FILE", tmp_path / "nonexistent.json")
    result = fetcher.load_progress()
    assert "completed" in result
    assert "companies" in result
    assert isinstance(result["completed"], list)
    assert isinstance(result["companies"], list)


def test_load_progress_returns_default_on_corrupt_file(tmp_path, monkeypatch):
    corrupt = tmp_path / "progress.json"
    corrupt.write_text("NOT VALID JSON }{")
    monkeypatch.setattr(fetcher, "PROGRESS_FILE", corrupt)
    result = fetcher.load_progress()
    assert "completed" in result
    assert "companies" in result


def test_get_companies_max_zero_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "PROGRESS_FILE", tmp_path / "progress.json")
    result = fetcher.get_companies_with_data(max_companies=0, resume=False)
    assert result == []
