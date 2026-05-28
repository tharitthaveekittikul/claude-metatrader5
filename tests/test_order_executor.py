import pytest
from unittest.mock import MagicMock
from src.response_parser import TradeDecision
from src.order_executor import (
    calculate_lot, validate_sl_tp, validate_pending_entry, execute_order,
)

RISK_CONFIG = {
    'risk_per_trade_pct': 1.0,
    'max_lot_hard_cap_pct': 5.0,
    'confidence_lot_multiplier': {'HIGH': 1.0, 'MEDIUM': 0.5, 'LOW': 0.25},
}
ACCOUNT = {'balance': 10000.0, 'equity': 10000.0, 'margin': 0.0, 'total_positions': 0}
SYM_INFO = {'trade_contract_size': 100.0, 'volume_min': 0.01, 'volume_max': 100.0, 'volume_step': 0.01}


def test_lot_calculation_high_confidence():
    lot = calculate_lot(10000.0, 1.0, 16.5, 100.0, 'HIGH', 0.01, 100.0, 0.01, 5.0)
    assert lot == pytest.approx(0.06, abs=0.01)


def test_lot_calculation_medium_confidence():
    lot_high = calculate_lot(10000.0, 1.0, 16.5, 100.0, 'HIGH', 0.01, 100.0, 0.01, 5.0)
    lot_med = calculate_lot(10000.0, 1.0, 16.5, 100.0, 'MEDIUM', 0.01, 100.0, 0.01, 5.0)
    assert lot_med == pytest.approx(lot_high * 0.5, abs=0.01)


def test_lot_respects_volume_min():
    lot = calculate_lot(100.0, 1.0, 100.0, 100.0, 'LOW', 0.01, 100.0, 0.01, 5.0)
    assert lot >= 0.01


def test_lot_respects_hard_cap():
    lot = calculate_lot(10000.0, 1.0, 0.001, 100.0, 'HIGH', 0.01, 100.0, 0.01, 5.0)
    max_allowed = 10000.0 * 0.05 / 100.0
    assert lot <= max_allowed + 0.01


def test_validate_sl_tp_buy_valid():
    d = TradeDecision('BUY', None, 2318.0, 2365.0, 'HIGH', None, 'test')
    assert validate_sl_tp(d, ask=2334.60) is True


def test_validate_sl_tp_buy_invalid_sl_above_entry():
    d = TradeDecision('BUY', None, 2360.0, 2365.0, 'HIGH', None, 'test')
    assert validate_sl_tp(d, ask=2334.60) is False


def test_validate_sl_tp_sell_invalid_sl_below_entry():
    d = TradeDecision('SELL', None, 2300.0, 2280.0, 'HIGH', None, 'test')
    assert validate_sl_tp(d, bid=2334.40) is False


def test_validate_pending_entry_buy_limit_valid():
    assert validate_pending_entry('BUY LIMIT', entry=2320.0, ask=2334.60, bid=2334.40) is True


def test_validate_pending_entry_buy_limit_invalid():
    assert validate_pending_entry('BUY LIMIT', entry=2340.0, ask=2334.60, bid=2334.40) is False


def test_validate_pending_entry_buy_stop_valid():
    assert validate_pending_entry('BUY STOP', entry=2350.0, ask=2334.60, bid=2334.40) is True


def test_validate_pending_entry_sell_limit_valid():
    assert validate_pending_entry('SELL LIMIT', entry=2350.0, ask=2334.60, bid=2334.40) is True


def test_validate_pending_entry_sell_stop_valid():
    assert validate_pending_entry('SELL STOP', entry=2320.0, ask=2334.60, bid=2334.40) is True


def test_execute_order_hold_returns_skipped():
    client = MagicMock()
    decision = TradeDecision('HOLD', None, None, None, 'LOW', None, 'no setup')
    result = execute_order(decision, 'XAUUSD', client, RISK_CONFIG, ACCOUNT)
    assert result['status'] == 'skipped'
    client.place_market_order.assert_not_called()


def test_execute_order_invalid_sl_tp_returns_rejected():
    client = MagicMock()
    client.get_symbol_price.return_value = {'bid': 2334.40, 'ask': 2334.60}
    client.get_symbol_info.return_value = SYM_INFO
    decision = TradeDecision('BUY', None, 2360.0, 2365.0, 'HIGH', None, 'test')
    result = execute_order(decision, 'XAUUSD', client, RISK_CONFIG, ACCOUNT)
    assert result['status'] == 'rejected'


def test_execute_market_order_calls_place_market_order():
    client = MagicMock()
    client.get_symbol_price.return_value = {'bid': 2334.40, 'ask': 2334.60}
    client.get_symbol_info.return_value = SYM_INFO
    client.place_market_order.return_value = {'order_id': 12345}
    decision = TradeDecision('BUY', None, 2318.0, 2365.0, 'HIGH', None, 'test')
    result = execute_order(decision, 'XAUUSD', client, RISK_CONFIG, ACCOUNT)
    assert result['status'] == 'executed'
    client.place_market_order.assert_called_once()
