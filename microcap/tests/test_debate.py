import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import debate


def _agent_result(verdict, confidence, governance_signal=None, symbol="TEST"):
    r = {
        "symbol": symbol, "name": "Test Co",
        "verdict": verdict, "confidence": confidence,
        "report": f"Test report: {verdict}",
    }
    if governance_signal is not None:
        r["governance_signal"] = governance_signal
    return r


def test_all_three_pass_shortlists():
    result = debate.debate(
        _agent_result("pass", 0.7),
        _agent_result("pass", 0.7),
        _agent_result("pass", 0.7, governance_signal="clean"),
    )
    assert result["final_verdict"] == "shortlist"


def test_laxmi_hard_reject_overrides():
    """Laxmi reject with confidence >= 0.8 → unconditional reject."""
    result = debate.debate(
        _agent_result("reject", 0.85),
        _agent_result("pass", 0.8),
        _agent_result("pass", 0.8, governance_signal="clean"),
    )
    assert result["final_verdict"] == "reject"


def test_two_pass_one_reject_borderline():
    """laxmi=pass(0.5) + meera=pass(0.5) + tara=reject(0.75) → borderline (norm≈0.08)."""
    result = debate.debate(
        _agent_result("pass", 0.5),
        _agent_result("pass", 0.5),
        _agent_result("reject", 0.75, governance_signal="clean"),
    )
    assert result["final_verdict"] == "borderline"


def test_all_three_reject():
    """All three reject (laxmi confidence < 0.8, no governance red flag) → reject."""
    result = debate.debate(
        _agent_result("reject", 0.7),
        _agent_result("reject", 0.7),
        _agent_result("reject", 0.7, governance_signal="clean"),
    )
    assert result["final_verdict"] == "reject"


def test_result_has_required_keys():
    result = debate.debate(
        _agent_result("pass", 0.7),
        _agent_result("pass", 0.7),
        _agent_result("pass", 0.7, governance_signal="clean"),
    )
    for key in ("final_verdict", "confidence", "debated"):
        assert key in result, f"Missing key: {key}"


def test_meera_tara_optional_defaults():
    """debate() should not crash when meera/tara are empty dicts."""
    result = debate.debate(
        _agent_result("reject", 0.85),
        {},
        {},
    )
    assert "final_verdict" in result


def test_tara_governance_red_flag_overrides():
    """Tara governance red_flag reject always wins regardless of other verdicts."""
    result = debate.debate(
        _agent_result("pass", 0.8),
        _agent_result("pass", 0.8),
        {"symbol": "TEST", "name": "Test Co", "verdict": "reject",
         "confidence": 0.85, "report": "governance", "governance_signal": "red_flag"},
    )
    assert result["final_verdict"] == "reject"
