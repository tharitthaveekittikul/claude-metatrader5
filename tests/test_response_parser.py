# tests/test_response_parser.py
import pytest
from src.response_parser import parse_response, TradeDecision

VALID_HOLD = """ORDER_TYPE: HOLD
ENTRY: N/A
STOP_LOSS: N/A
TAKE_PROFIT: N/A
CONFIDENCE: LOW
EXPIRY: N/A
REASON: No clear setup."""

VALID_BUY_LIMIT = """ORDER_TYPE: BUY LIMIT
ENTRY: 2334.50
STOP_LOSS: 2318.00
TAKE_PROFIT: 2365.00
CONFIDENCE: HIGH
EXPIRY: 6h
REASON: H1 trend bullish, M15 RSI oversold at support."""

VALID_SELL = """ORDER_TYPE: SELL
ENTRY: N/A
STOP_LOSS: 2370.00
TAKE_PROFIT: 2320.00
CONFIDENCE: MEDIUM
EXPIRY: N/A
REASON: Strong bearish momentum confirmed."""


def test_parse_hold():
    d = parse_response(VALID_HOLD)
    assert d.order_type == 'HOLD'
    assert d.entry is None
    assert d.stop_loss is None
    assert d.take_profit is None
    assert d.confidence == 'LOW'
    assert d.expiry_hours is None


def test_parse_buy_limit():
    d = parse_response(VALID_BUY_LIMIT)
    assert d.order_type == 'BUY LIMIT'
    assert d.entry == 2334.50
    assert d.stop_loss == 2318.00
    assert d.take_profit == 2365.00
    assert d.confidence == 'HIGH'
    assert d.expiry_hours == 6.0


def test_parse_market_sell():
    d = parse_response(VALID_SELL)
    assert d.order_type == 'SELL'
    assert d.entry is None
    assert d.expiry_hours is None
    assert d.confidence == 'MEDIUM'


def test_invalid_order_type_returns_hold():
    raw = VALID_HOLD.replace('ORDER_TYPE: HOLD', 'ORDER_TYPE: MAYBE')
    d = parse_response(raw)
    assert d.order_type == 'HOLD'
    assert 'Parse error' in d.reason


def test_missing_field_returns_hold():
    raw = "ORDER_TYPE: BUY\nSTOP_LOSS: 2318\n"
    d = parse_response(raw)
    assert d.order_type == 'HOLD'


def test_invalid_expiry_returns_hold():
    raw = VALID_BUY_LIMIT.replace('EXPIRY: 6h', 'EXPIRY: tomorrow')
    d = parse_response(raw)
    assert d.order_type == 'HOLD'


def test_all_valid_order_types():
    valid_types = ['BUY', 'BUY LIMIT', 'BUY STOP', 'SELL', 'SELL LIMIT', 'SELL STOP', 'HOLD']
    for ot in valid_types:
        raw = f"ORDER_TYPE: {ot}\nENTRY: N/A\nSTOP_LOSS: N/A\nTAKE_PROFIT: N/A\nCONFIDENCE: LOW\nEXPIRY: N/A\nREASON: test"
        d = parse_response(raw)
        assert d.order_type == ot
