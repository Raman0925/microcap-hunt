import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import meera


def _make_company(
    current_price=None,
    high_52w=None,
    low_52w=None,
    revenue_series=None,
    symbol="TEST",
):
    """Build a company dict with the fields meera.analyse() actually reads."""
    company = {"symbol": symbol, "name": "Test Company Ltd"}
    if current_price is not None:
        company["current_price"] = str(current_price)
    if high_52w is not None:
        company["52w_high"] = high_52w
    if low_52w is not None:
        company["52w_low"] = low_52w
    if revenue_series is not None:
        row = {"Metric": "Sales"}
        for i, v in enumerate(revenue_series):
            row[f"Y{i}"] = str(v)
        company["profit_loss"] = [row]
    return company


def test_near_52w_high_bullish():
    """Price 94% up the 52w range → bullish (price within 30% of high + above midpoint)."""
    # high=180, low=100, price=175 → from_high=(180-175)/180*100=2.8%, pos=93.8%
    company = _make_company(current_price=175, high_52w=180, low_52w=100)
    result = meera.analyse(company)
    assert result["verdict"] != "reject"
    assert result["price_signal"] == "bullish"


def test_near_52w_low_bearish():
    """Price close to 52w low → bearish (far from high, below midpoint)."""
    # high=180, low=100, price=105 → from_high=41.7%, pos=6.3% → 0 price signals
    company = _make_company(current_price=105, high_52w=180, low_52w=100)
    result = meera.analyse(company)
    assert result["verdict"] in ("reject", "borderline")
    assert result["price_signal"] in ("bearish", "neutral")


def test_missing_price_data_no_crash():
    result = meera.analyse({})
    assert isinstance(result, dict)


def test_result_has_required_keys():
    result = meera.analyse({"symbol": "X"})
    for key in ("verdict", "score", "confidence", "report"):
        assert key in result, f"Missing key: {key}"


def test_revenue_growth_adds_signal():
    """Growing revenue (2nd year > 3rd year when sorted recent-first) adds +1."""
    # revenue_series is stored most-recent first in the table row by column order
    company = _make_company(
        current_price=150,
        high_52w=180,
        low_52w=100,
        revenue_series=[90, 80, 70],  # growing YoY
    )
    result = meera.analyse(company)
    assert result["revenue_momentum"] == "growing"


def test_score_bounds():
    """Score is always in 0-3 range."""
    result = meera.analyse({"symbol": "X", "current_price": "abc", "52w_high": None})
    assert 0 <= result["score"] <= 3
