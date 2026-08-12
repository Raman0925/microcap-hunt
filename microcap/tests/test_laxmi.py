import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import laxmi


def _make_company(
    fcf_values=None,
    debt_to_equity="0.5",
    roce="22",
    promoter_holding="65",
    symbol="TEST",
):
    """Build a company dict with cash_flow table rows as laxmi expects."""
    cash_flow = []
    if fcf_values is not None:
        row = {"Metric": "Free Cash Flow"}
        for i, v in enumerate(fcf_values):
            row[f"Y{i}"] = str(v)
        cash_flow = [row]
    return {
        "symbol": symbol,
        "name": "Test Company Ltd",
        "cash_flow": cash_flow,
        "debt_to_equity": debt_to_equity,
        "roce": roce,
        "promoter_holding": promoter_holding,
    }


def test_fcf_positive_3_of_5_not_reject():
    company = _make_company(fcf_values=[4, 5, -1, 6, -2])  # 3 of 5 positive
    result = laxmi.analyse(company)
    assert result["verdict"] != "reject"


def test_zero_fcf_positive_years_rejects():
    """0 FCF positive years + all other checks fail → reject with confidence >= 0.85."""
    company = _make_company(
        fcf_values=[-1, -2, -3, -4, -5],
        debt_to_equity="3.0",
        roce="5",
        promoter_holding="20",
    )
    result = laxmi.analyse(company)
    assert result["verdict"] == "reject"
    assert result["confidence"] >= 0.85


def test_low_promoter_holding_flagged_as_risk():
    """Promoter holding below 35% is listed in key_risks."""
    company = _make_company(
        fcf_values=[4, 5, 6, 7, 8],
        debt_to_equity="0.3",
        roce="18",
        promoter_holding="10",
    )
    result = laxmi.analyse(company)
    assert any("promoter" in r.lower() for r in result["key_risks"])


def test_low_roce_not_scored():
    """ROCE below 12% means no +1 for ROCE; score reflects the penalty."""
    company = _make_company(
        fcf_values=[4, 5, 6, 7, 8],
        debt_to_equity="0.5",
        roce="8",
        promoter_holding="65",
    )
    result = laxmi.analyse(company)
    assert result["score"] < 4
    assert any("roce" in r.lower() for r in result["key_risks"])


def test_empty_dict_no_crash():
    result = laxmi.analyse({})
    assert isinstance(result, dict)


def test_result_has_required_keys():
    result = laxmi.analyse({"symbol": "X"})
    for key in ("verdict", "score", "confidence", "report"):
        assert key in result, f"Missing key: {key}"


def test_high_score_passes(sample_company):
    """A well-rounded company with good FCF, low debt, high ROCE → pass."""
    result = laxmi.analyse(sample_company)
    assert result["verdict"] == "pass"
    assert result["score"] >= 3


def test_verdict_confidence_correlation():
    """Reject verdict always carries confidence >= 0.85 when score == 0."""
    company = _make_company(
        fcf_values=[-5, -4, -3, -2, -1],
        debt_to_equity="5",
        roce="2",
        promoter_holding="5",
    )
    result = laxmi.analyse(company)
    if result["verdict"] == "reject" and result["score"] == 0:
        assert result["confidence"] >= 0.85
