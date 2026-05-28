# tests/test_prompt_builder.py
from src.prompt_builder import build_prompt, format_positions, format_pending, format_closed_trades

SAMPLE_PRICE = {'bid': 2334.40, 'ask': 2334.60, 'spread': 2.0}
SAMPLE_H1 = {
    'ma20': 2320.0, 'ma50': 2300.0, 'ma200': 2250.0,
    'rsi': 58.3, 'macd': 1.2, 'macd_signal': 0.8, 'macd_hist': 0.4,
    'atr': 12.5, 'bb_upper': 2360.0, 'bb_mid': 2320.0, 'bb_lower': 2280.0,
    'last_3_candles': ['Bullish', 'Doji', 'Bullish'],
}
SAMPLE_M15 = {
    'ma20': 2330.0, 'ma50': 2325.0,
    'rsi': 38.2, 'macd': -0.3, 'macd_signal': -0.1, 'macd_hist': -0.2,
    'atr': 3.8, 'bb_upper': 2345.0, 'bb_mid': 2332.0, 'bb_lower': 2319.0,
    'last_3_candles': ['Bearish', 'Bearish', 'Doji'],
}
SAMPLE_ACCOUNT = {
    'balance': 10000.0, 'equity': 10150.0, 'margin': 200.0, 'total_positions': 1,
}


def test_prompt_contains_symbol():
    prompt = build_prompt('XAUUSD', SAMPLE_PRICE, SAMPLE_H1, SAMPLE_M15,
                          'BULLISH', SAMPLE_ACCOUNT, [], [], [], max_trades=5)
    assert 'XAUUSD' in prompt


def test_prompt_contains_trend_bias():
    prompt = build_prompt('XAUUSD', SAMPLE_PRICE, SAMPLE_H1, SAMPLE_M15,
                          'BULLISH', SAMPLE_ACCOUNT, [], [], [], max_trades=5)
    assert 'BULLISH' in prompt


def test_prompt_contains_price_values():
    prompt = build_prompt('XAUUSD', SAMPLE_PRICE, SAMPLE_H1, SAMPLE_M15,
                          'BULLISH', SAMPLE_ACCOUNT, [], [], [], max_trades=5)
    assert '2334.40' in prompt
    assert '2334.60' in prompt


def test_prompt_contains_account_balance():
    prompt = build_prompt('XAUUSD', SAMPLE_PRICE, SAMPLE_H1, SAMPLE_M15,
                          'BULLISH', SAMPLE_ACCOUNT, [], [], [], max_trades=5)
    assert '10000.0' in prompt


def test_prompt_contains_response_format():
    prompt = build_prompt('XAUUSD', SAMPLE_PRICE, SAMPLE_H1, SAMPLE_M15,
                          'BULLISH', SAMPLE_ACCOUNT, [], [], [], max_trades=5)
    assert 'ORDER_TYPE:' in prompt
    assert 'STOP_LOSS:' in prompt
    assert 'CONFIDENCE:' in prompt


def test_format_positions_empty():
    assert format_positions([]) == 'none'


def test_format_positions_with_data():
    positions = [{'type': 'BUY', 'volume': 0.01, 'price_open': 2330.0, 'sl': 2318.0, 'tp': 2360.0, 'profit': 45.0}]
    result = format_positions(positions)
    assert 'BUY' in result
    assert '2330.0' in result
    assert '$45.00' in result


def test_format_closed_trades_empty():
    assert format_closed_trades([]) == 'none'


def test_format_closed_trades_shows_win_loss():
    trades = [
        {'type': 'BUY', 'profit': 48.0, 'time': '2026-05-28 10:00'},
        {'type': 'SELL', 'profit': -25.0, 'time': '2026-05-28 08:00'},
    ]
    result = format_closed_trades(trades)
    assert 'WIN' in result
    assert 'LOSS' in result
