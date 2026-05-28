# tests/test_dashboard_helpers.py
import json
import pytest
from pathlib import Path


def load_state(state_path: Path) -> dict:
    """Copy of the helper — tested independently before wiring into dashboard."""
    if not state_path.exists():
        return {"symbols": {}, "totals": {}, "call_history": []}
    with open(state_path) as f:
        return json.load(f)


def test_load_state_missing_file(tmp_path):
    result = load_state(tmp_path / "nonexistent.json")
    assert result == {"symbols": {}, "totals": {}, "call_history": []}


def test_load_state_existing_file(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "symbols": {
            "XAUUSD.s": {
                "last_signal": {"order_type": "BUY LIMIT", "confidence": "HIGH"},
                "last_result": {"status": "executed"},
                "updated_at": "2026-05-28T14:00:00",
            }
        },
        "totals": {"calls": 5, "cost_usd": 0.012, "input_tokens": 1000, "output_tokens": 200},
        "call_history": [{"time": "2026-05-28T14:00:00", "symbol": "XAUUSD.s",
                          "decision": "BUY LIMIT", "confidence": "HIGH",
                          "status": "executed", "cost_usd": 0.002}],
    }))
    result = load_state(state_file)
    assert result["symbols"]["XAUUSD.s"]["last_signal"]["order_type"] == "BUY LIMIT"
    assert result["totals"]["calls"] == 5
    assert len(result["call_history"]) == 1


def test_load_state_empty_file(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"symbols": {}}))
    result = load_state(state_file)
    assert result["symbols"] == {}
    assert result.get("totals", {}) == {}
