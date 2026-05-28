import pytest
from unittest.mock import patch
from src.state_manager import load_state, save_state, update_symbol_state, get_last_m15_candle_time


@pytest.fixture
def tmp_state_file(tmp_path):
    state_path = str(tmp_path / 'state.json')
    with patch('src.state_manager.STATE_FILE', state_path):
        yield state_path


def test_load_state_returns_empty_if_no_file(tmp_state_file):
    state = load_state()
    assert state == {'symbols': {}, 'last_cycle': None}


def test_save_and_load_state(tmp_state_file):
    data = {'symbols': {'XAUUSD': {'order_type': 'BUY'}}, 'last_cycle': '2026-05-28T10:00'}
    save_state(data)
    loaded = load_state()
    assert loaded['symbols']['XAUUSD']['order_type'] == 'BUY'


def test_update_symbol_state_creates_entry(tmp_state_file):
    update_symbol_state('XAUUSD', {'order_type': 'SELL'}, '2026-05-28 10:15', {'status': 'executed'})
    state = load_state()
    assert 'XAUUSD' in state['symbols']
    assert state['symbols']['XAUUSD']['last_signal']['order_type'] == 'SELL'
    assert state['symbols']['XAUUSD']['m15_candle_time'] == '2026-05-28 10:15'


def test_get_last_m15_candle_time_none_if_missing(tmp_state_file):
    assert get_last_m15_candle_time('XAUUSD') is None


def test_get_last_m15_candle_time_returns_stored(tmp_state_file):
    update_symbol_state('XAUUSD', {}, '2026-05-28 10:15', {})
    assert get_last_m15_candle_time('XAUUSD') == '2026-05-28 10:15'
