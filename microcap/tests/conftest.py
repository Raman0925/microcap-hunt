import pytest
import json
import tempfile
from pathlib import Path


@pytest.fixture
def sample_company():
    return {
        "symbol": "TEST",
        "name": "Test Company Ltd",
        "market_cap_cr": 250,
        "current_price": "150",
        "52w_high": 180,
        "52w_low": 100,
        "debt_to_equity": "0.25",
        "roce": "22",
        "promoter_holding": "65",
        "about": (
            "Test Company Ltd is a well-established manufacturing conglomerate "
            "operating across multiple verticals including engineering, chemicals, "
            "and consumer goods with over 30 years of industry experience."
        ),
        "shareholding_raw": "Promoter: 65%. Pledged: 0%.",
        "cash_flow": [
            {
                "Metric": "Net Profit",
                "2023": "9", "2022": "8", "2021": "7", "2020": "6", "2019": "5",
            },
            {
                "Metric": "Free Cash Flow",
                "2023": "8", "2022": "7", "2021": "6", "2020": "5", "2019": "4",
            },
        ],
        "profit_loss": [
            {
                "Metric": "Sales",
                "2023": "90", "2022": "80", "2021": "70", "2020": "60", "2019": "50",
            },
        ],
    }


@pytest.fixture
def pass_result():
    return {"verdict": "pass", "score": 8, "confidence": 0.8, "report": "pass"}


@pytest.fixture
def fail_result():
    return {"verdict": "reject", "score": 2, "confidence": 0.9, "report": "fail"}
