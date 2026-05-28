from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

import MetaTrader5 as mt5


class MT5Client:
    def __init__(self, config: dict):
        self.config = config

    def connect(self) -> bool:
        return mt5.initialize(
            login=self.config['mt5']['login'],
            password=self.config['mt5']['password'],
            server=self.config['mt5']['server'],
        )

    def disconnect(self):
        mt5.shutdown()

    def get_candles(self, symbol: str, timeframe: int, count: int) -> pd.DataFrame:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            raise ValueError(f"Failed to get candles for {symbol}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_symbol_price(self, symbol: str) -> dict:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ValueError(f"Failed to get price for {symbol}")
        info = mt5.symbol_info(symbol)
        spread = round((tick.ask - tick.bid) / info.point, 1) if info else 0
        return {'bid': tick.bid, 'ask': tick.ask, 'spread': spread}

    def get_account_info(self) -> dict:
        info = mt5.account_info()
        if info is None:
            raise ValueError("Failed to get account info")
        return {
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
        }

    def get_open_positions(self, symbol: Optional[str] = None) -> list:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if positions is None:
            return []
        return [self._position_to_dict(p) for p in positions]

    def get_pending_orders(self, symbol: Optional[str] = None) -> list:
        orders = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
        if orders is None:
            return []
        return [self._order_to_dict(o) for o in orders]

    def get_closed_trades(self, symbol: str, max_trades: int, lookback_hours: int) -> list:
        from_date = datetime.now() - timedelta(hours=lookback_hours)
        deals = mt5.history_deals_get(from_date, datetime.now(), group=symbol)
        if deals is None:
            return []
        entry_deals = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
        return [self._deal_to_dict(d) for d in entry_deals[-max_trades:]]

    def get_symbol_info(self, symbol: str) -> dict:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"Symbol {symbol} not found")
        return {
            'trade_contract_size': info.trade_contract_size,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'digits': info.digits,
            'point': info.point,
        }

    def place_market_order(self, symbol: str, order_type: str, volume: float,
                           sl: Optional[float], tp: Optional[float]) -> dict:
        mt5_type = mt5.ORDER_TYPE_BUY if order_type == 'BUY' else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type == 'BUY' else tick.bid

        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol, 'volume': volume, 'type': mt5_type, 'price': price,
            'sl': sl or 0.0, 'tp': tp or 0.0,
            'deviation': 20, 'magic': 234000, 'comment': 'claude-mt5',
            'type_time': mt5.ORDER_TIME_GTC, 'type_filling': mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise ValueError(f"Market order failed: {result.retcode} {result.comment}")
        return {'order_id': result.order, 'retcode': result.retcode}

    def place_pending_order(self, symbol: str, order_type: str, volume: float,
                            entry: float, sl: Optional[float], tp: Optional[float],
                            expiry_hours: float) -> dict:
        type_map = {
            'BUY LIMIT': mt5.ORDER_TYPE_BUY_LIMIT,
            'BUY STOP': mt5.ORDER_TYPE_BUY_STOP,
            'SELL LIMIT': mt5.ORDER_TYPE_SELL_LIMIT,
            'SELL STOP': mt5.ORDER_TYPE_SELL_STOP,
        }
        expiry_time = datetime.now() + timedelta(hours=expiry_hours)

        request = {
            'action': mt5.TRADE_ACTION_PENDING,
            'symbol': symbol, 'volume': volume, 'type': type_map[order_type],
            'price': entry, 'sl': sl or 0.0, 'tp': tp or 0.0,
            'expiration': expiry_time,
            'deviation': 20, 'magic': 234000, 'comment': 'claude-mt5',
            'type_time': mt5.ORDER_TIME_SPECIFIED, 'type_filling': mt5.ORDER_FILLING_RETURN,
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise ValueError(f"Pending order failed: {result.retcode} {result.comment}")
        return {'order_id': result.order, 'retcode': result.retcode}

    def _position_to_dict(self, p) -> dict:
        return {
            'ticket': p.ticket, 'symbol': p.symbol,
            'type': 'BUY' if p.type == mt5.ORDER_TYPE_BUY else 'SELL',
            'volume': p.volume, 'price_open': p.price_open,
            'sl': p.sl, 'tp': p.tp, 'profit': p.profit,
        }

    def _order_to_dict(self, o) -> dict:
        type_map = {
            mt5.ORDER_TYPE_BUY_LIMIT: 'BUY LIMIT', mt5.ORDER_TYPE_BUY_STOP: 'BUY STOP',
            mt5.ORDER_TYPE_SELL_LIMIT: 'SELL LIMIT', mt5.ORDER_TYPE_SELL_STOP: 'SELL STOP',
        }
        return {
            'ticket': o.ticket, 'symbol': o.symbol,
            'type': type_map.get(o.type, str(o.type)),
            'volume': o.volume_current, 'price': o.price_open, 'sl': o.sl, 'tp': o.tp,
        }

    def _deal_to_dict(self, d) -> dict:
        return {
            'ticket': d.ticket, 'symbol': d.symbol,
            'type': 'BUY' if d.type == mt5.DEAL_TYPE_BUY else 'SELL',
            'volume': d.volume, 'price': d.price, 'profit': d.profit,
            'time': datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M'),
        }
