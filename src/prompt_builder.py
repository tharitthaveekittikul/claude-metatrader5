from datetime import datetime


def get_session(dt: datetime) -> str:
    hour = dt.hour
    sessions = []
    if 0 <= hour < 8:
        sessions.append('Asian')
    if 8 <= hour < 16:
        sessions.append('London')
    if 13 <= hour < 22:
        sessions.append('New York')
    return '/'.join(sessions) if sessions else 'Off-Hours'


def format_positions(positions: list) -> str:
    if not positions:
        return 'none'
    parts = []
    for p in positions:
        parts.append(
            f"{p['type']} {p['volume']} lot @ {p['price_open']}, "
            f"SL={p['sl']}, TP={p['tp']}, P&L=${p['profit']:.2f}"
        )
    return '; '.join(parts)


def format_pending(orders: list) -> str:
    if not orders:
        return 'none'
    parts = []
    for o in orders:
        parts.append(f"{o['type']} {o['volume']} lot @ {o['price']}, SL={o['sl']}, TP={o['tp']}")
    return '; '.join(parts)


def format_closed_trades(trades: list) -> str:
    if not trades:
        return 'none'
    lines = []
    for i, t in enumerate(trades, 1):
        result = 'WIN' if t['profit'] > 0 else 'LOSS'
        lines.append(f"{i}. {t['type']} → {result} (${t['profit']:.2f}) — {t['time']}")
    return '\n'.join(lines)


def build_prompt(symbol: str, price: dict, h1_indicators: dict, m15_indicators: dict,
                 trend_bias: str, account: dict, open_positions: list,
                 pending_orders: list, closed_trades: list, max_trades: int) -> str:
    now = datetime.now()
    session = get_session(now)
    price_vs_ma20 = 'above' if price['ask'] > (h1_indicators.get('ma20') or 0) else 'below'

    return f"""You are an expert technical analyst and trader. Analyze {symbol} and return a single trading decision. Trade ONLY in the direction of the H1 trend. Output HOLD when signals conflict or confidence is low.

## Market Context
Symbol: {symbol}
Analysis Time: {now.strftime('%Y-%m-%d %H:%M')} ({session} session)
Current Price: Bid={price['bid']:.2f} | Ask={price['ask']:.2f}
Spread: {price['spread']} pips

## H1 Timeframe (Trend Direction)
Trend Bias: {trend_bias}
MA20: {h1_indicators.get('ma20')} | MA50: {h1_indicators.get('ma50')} | MA200: {h1_indicators.get('ma200')}
Price vs MA20: {price_vs_ma20}
RSI(14): {h1_indicators.get('rsi')}
MACD: {h1_indicators.get('macd')} | Signal: {h1_indicators.get('macd_signal')} | Histogram: {h1_indicators.get('macd_hist')}
Bollinger: Upper={h1_indicators.get('bb_upper')} | Mid={h1_indicators.get('bb_mid')} | Lower={h1_indicators.get('bb_lower')}
ATR(14): {h1_indicators.get('atr')}
Last 3 candles: {h1_indicators.get('last_3_candles')}

## M15 Timeframe (Entry Timing)
MA20: {m15_indicators.get('ma20')} | MA50: {m15_indicators.get('ma50')}
RSI(14): {m15_indicators.get('rsi')}
MACD: {m15_indicators.get('macd')} | Signal: {m15_indicators.get('macd_signal')} | Histogram: {m15_indicators.get('macd_hist')}
Bollinger: Upper={m15_indicators.get('bb_upper')} | Mid={m15_indicators.get('bb_mid')} | Lower={m15_indicators.get('bb_lower')}
ATR(14): {m15_indicators.get('atr')}
Last 3 candles: {m15_indicators.get('last_3_candles')}

## Account
Balance: {account['balance']}
Equity: {account['equity']}
Used Margin: {account['margin']}
Total Open Positions (all symbols): {account['total_positions']}

## Current Positions & Orders for {symbol}
Open positions: {format_positions(open_positions)}
Pending orders: {format_pending(pending_orders)}

## Recent Closed Trades ({symbol}, last {max_trades} within 24h)
{format_closed_trades(closed_trades)}

## Decision Rules
- Trade ONLY in H1 trend direction (BULLISH = BUY side only, BEARISH = SELL side only)
- HOLD if H1 trend is NEUTRAL or signals conflict
- HOLD if an open position already exists in same direction
- HOLD if same direction was stopped out in last 2 trades (unless HIGH confidence)
- HOLD if pending order already exists (unless significantly better setup)
- For LIMIT/STOP orders: set EXPIRY between 1h-24h based on setup quality

## Response Format (STRICT — output ONLY these lines, no extra text)
ORDER_TYPE: [BUY|BUY LIMIT|BUY STOP|SELL|SELL LIMIT|SELL STOP|HOLD]
ENTRY: [price for pending orders | N/A for market orders or HOLD]
STOP_LOSS: [price | N/A for HOLD]
TAKE_PROFIT: [price | N/A for HOLD]
CONFIDENCE: [HIGH|MEDIUM|LOW]
EXPIRY: [e.g. 4h | N/A for market orders or HOLD]
REASON: [2-3 sentences max]"""
