import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tara
from unittest.mock import patch

LONG_ABOUT = (
    "A well-established manufacturing conglomerate with diversified operations "
    "spanning engineering, chemicals, consumer goods, and exports to 30+ countries."
)


def _mock_news(headlines=None, positive=0, negative=0):
    return (headlines or [], positive, negative)


def test_promoter_pledging_above_30_flags_red():
    company = {
        "symbol": "TEST", "name": "Test Co",
        "about": LONG_ABOUT,
        "shareholding_raw": "Promoter: 60%. Pledged: 35% of promoter holdings.",
    }
    with patch("tara._search_news", return_value=_mock_news(["some news"], 1, 0)):
        result = tara.analyse(company)
    assert "Promoter pledging > 30%" in result["red_flags"]
    assert result["governance_signal"] == "red_flag"


def test_risky_sector_flagged():
    company = {
        "symbol": "TEST", "name": "Test Co",
        "about": "A psu bank offering retail banking services across rural India with strong NPA management.",
        "shareholding_raw": "",
    }
    with patch("tara._search_news", return_value=_mock_news()):
        result = tara.analyse(company)
    assert any("psu bank" in flag.lower() or "sector" in flag.lower() for flag in result["red_flags"])
    assert result["sector_view"] == "negative"


def test_short_about_shell_company_flagged():
    company = {
        "symbol": "TEST", "name": "Test Co",
        "about": "Small firm.",  # < 80 chars
        "shareholding_raw": "",
    }
    with patch("tara._search_news", return_value=_mock_news()):
        result = tara.analyse(company)
    assert any("shell" in flag.lower() or "short" in flag.lower() for flag in result["red_flags"])


def test_missing_data_no_crash():
    with patch("tara._search_news", return_value=_mock_news()):
        result = tara.analyse({})
    assert isinstance(result, dict)


def test_result_has_required_keys():
    with patch("tara._search_news", return_value=_mock_news()):
        result = tara.analyse({"symbol": "X"})
    for key in ("verdict", "score", "confidence", "report"):
        assert key in result, f"Missing key: {key}"


def test_clean_company_passes():
    company = {
        "symbol": "TEST", "name": "Test Co",
        "about": LONG_ABOUT,
        "shareholding_raw": "Promoter: 65%. Pledged: 0%.",
    }
    with patch("tara._search_news", return_value=_mock_news(
        ["record profit announced", "strong growth reported", "order win secured"],
        positive=3, negative=0,
    )):
        result = tara.analyse(company)
    assert result["verdict"] in ("pass", "borderline")
    assert result["governance_signal"] == "clean"
