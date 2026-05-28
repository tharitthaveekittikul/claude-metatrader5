# tests/test_indicators.py
import pytest
from src.indicators import calculate_indicators, determine_trend_bias


def test_calculate_indicators_returns_all_keys(sample_ohlcv):
    result = calculate_indicators(
        df=sample_ohlcv,
        ma_periods=[20, 50, 200],
        rsi_period=14,
        atr_period=14,
        bollinger=[20, 2],
    )
    assert 'ma20' in result
    assert 'ma50' in result
    assert 'ma200' in result
    assert 'rsi' in result
    assert 'macd' in result
    assert 'macd_signal' in result
    assert 'macd_hist' in result
    assert 'atr' in result
    assert 'bb_upper' in result
    assert 'bb_mid' in result
    assert 'bb_lower' in result
    assert 'last_3_candles' in result


def test_indicators_are_floats(sample_ohlcv):
    result = calculate_indicators(sample_ohlcv, [20, 50, 200], 14, 14, [20, 2])
    assert isinstance(result['rsi'], float)
    assert isinstance(result['atr'], float)
    assert isinstance(result['ma20'], float)


def test_rsi_in_valid_range(sample_ohlcv):
    result = calculate_indicators(sample_ohlcv, [20], 14, 14, [20, 2])
    assert 0 <= result['rsi'] <= 100


def test_bollinger_band_order(sample_ohlcv):
    result = calculate_indicators(sample_ohlcv, [20], 14, 14, [20, 2])
    assert result['bb_lower'] < result['bb_mid'] < result['bb_upper']


def test_last_3_candles_valid_values(sample_ohlcv):
    result = calculate_indicators(sample_ohlcv, [20], 14, 14, [20, 2])
    assert len(result['last_3_candles']) == 3
    for d in result['last_3_candles']:
        assert d in ('Bullish', 'Bearish', 'Doji')


def test_trend_bias_bullish():
    indicators = {'ma20': 2100.0, 'ma50': 2050.0, 'ma200': 2000.0}
    assert determine_trend_bias(indicators, current_price=2150.0) == 'BULLISH'


def test_trend_bias_bearish():
    indicators = {'ma20': 2000.0, 'ma50': 2050.0, 'ma200': 2100.0}
    assert determine_trend_bias(indicators, current_price=1950.0) == 'BEARISH'


def test_trend_bias_neutral_mixed():
    indicators = {'ma20': 2050.0, 'ma50': 2000.0, 'ma200': 2100.0}
    assert determine_trend_bias(indicators, current_price=2080.0) == 'NEUTRAL'


def test_trend_bias_neutral_missing_ma():
    indicators = {'ma20': None, 'ma50': 2050.0, 'ma200': 2000.0}
    assert determine_trend_bias(indicators, current_price=2150.0) == 'NEUTRAL'
