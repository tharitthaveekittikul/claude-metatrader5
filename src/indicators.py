import pandas as pd
import pandas_ta as ta
from typing import Optional


def calculate_indicators(df: pd.DataFrame, ma_periods: list, rsi_period: int,
                         atr_period: int, bollinger: list) -> dict:
    close = df['close']
    high = df['high']
    low = df['low']
    open_ = df['open']
    result = {}

    for period in ma_periods:
        series = ta.ema(close, length=period)
        result[f'ma{period}'] = round(float(series.iloc[-1]), 5) if series is not None and not series.isna().all() else None

    rsi = ta.rsi(close, length=rsi_period)
    result['rsi'] = round(float(rsi.iloc[-1]), 2) if rsi is not None and not rsi.isna().all() else None

    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        macd_col = next((c for c in macd.columns if c.startswith('MACD_')), None)
        sig_col = next((c for c in macd.columns if c.startswith('MACDs_')), None)
        hist_col = next((c for c in macd.columns if c.startswith('MACDh_')), None)
        result['macd'] = round(float(macd[macd_col].iloc[-1]), 5) if macd_col else None
        result['macd_signal'] = round(float(macd[sig_col].iloc[-1]), 5) if sig_col else None
        result['macd_hist'] = round(float(macd[hist_col].iloc[-1]), 5) if hist_col else None
    else:
        result['macd'] = result['macd_signal'] = result['macd_hist'] = None

    atr = ta.atr(high, low, close, length=atr_period)
    result['atr'] = round(float(atr.iloc[-1]), 5) if atr is not None and not atr.isna().all() else None

    bb = ta.bbands(close, length=bollinger[0], std=bollinger[1])
    if bb is not None and not bb.empty:
        lower_col = next((c for c in bb.columns if c.startswith('BBL_')), None)
        mid_col = next((c for c in bb.columns if c.startswith('BBM_')), None)
        upper_col = next((c for c in bb.columns if c.startswith('BBU_')), None)
        result['bb_lower'] = round(float(bb[lower_col].iloc[-1]), 5) if lower_col else None
        result['bb_mid'] = round(float(bb[mid_col].iloc[-1]), 5) if mid_col else None
        result['bb_upper'] = round(float(bb[upper_col].iloc[-1]), 5) if upper_col else None
    else:
        result['bb_lower'] = result['bb_mid'] = result['bb_upper'] = None

    directions = []
    for i in [-3, -2, -1]:
        row = df.iloc[i]
        diff = row['close'] - row['open']
        candle_range = row['high'] - row['low']
        if candle_range > 0 and abs(diff) < candle_range * 0.1:
            directions.append('Doji')
        elif diff > 0:
            directions.append('Bullish')
        else:
            directions.append('Bearish')
    result['last_3_candles'] = directions

    return result


def determine_trend_bias(indicators_h1: dict, current_price: float) -> str:
    ma20 = indicators_h1.get('ma20')
    ma50 = indicators_h1.get('ma50')
    ma200 = indicators_h1.get('ma200')

    if ma20 is None or ma50 is None or ma200 is None:
        return 'NEUTRAL'
    if current_price > ma20 > ma50 > ma200:
        return 'BULLISH'
    if current_price < ma20 < ma50 < ma200:
        return 'BEARISH'
    return 'NEUTRAL'
