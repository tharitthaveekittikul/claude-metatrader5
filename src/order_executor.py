from typing import Optional
from .response_parser import TradeDecision

CONFIDENCE_MULTIPLIER = {'HIGH': 1.0, 'MEDIUM': 0.5, 'LOW': 0.25}


def calculate_lot(account_balance: float, risk_pct: float, sl_distance: float,
                  contract_size: float, confidence: str,
                  volume_min: float, volume_max: float, volume_step: float,
                  max_lot_cap_pct: float) -> float:
    risk_amount = account_balance * (risk_pct / 100)
    if sl_distance <= 0:
        return volume_min
    raw_lot = (risk_amount / (sl_distance * contract_size)) * CONFIDENCE_MULTIPLIER[confidence]
    max_allowed = account_balance * (max_lot_cap_pct / 100) / contract_size
    raw_lot = min(raw_lot, max_allowed)
    raw_lot = max(volume_min, min(volume_max, raw_lot))
    steps = round(raw_lot / volume_step)
    return round(max(1, steps) * volume_step, 8)


def validate_sl_tp(decision: TradeDecision, ask: float = 0, bid: float = 0) -> bool:
    ref_price = ask if 'BUY' in decision.order_type else bid
    entry = decision.entry if decision.entry else ref_price

    if 'BUY' in decision.order_type:
        if decision.stop_loss and decision.stop_loss >= entry:
            return False
        if decision.take_profit and decision.take_profit <= entry:
            return False
    elif 'SELL' in decision.order_type:
        if decision.stop_loss and decision.stop_loss <= entry:
            return False
        if decision.take_profit and decision.take_profit >= entry:
            return False
    return True


def validate_pending_entry(order_type: str, entry: float, ask: float, bid: float) -> bool:
    rules = {
        'BUY LIMIT': entry < ask,
        'BUY STOP': entry > ask,
        'SELL LIMIT': entry > bid,
        'SELL STOP': entry < bid,
    }
    return rules.get(order_type, True)


def execute_order(decision: TradeDecision, symbol: str, client, risk_config: dict, account: dict) -> dict:
    if decision.order_type == 'HOLD':
        return {'status': 'skipped', 'reason': decision.reason}

    price = client.get_symbol_price(symbol)
    sym_info = client.get_symbol_info(symbol)

    if not validate_sl_tp(decision, ask=price['ask'], bid=price['bid']):
        return {'status': 'rejected', 'reason': f"Invalid SL/TP for {decision.order_type}"}

    if decision.order_type in ('BUY LIMIT', 'BUY STOP', 'SELL LIMIT', 'SELL STOP'):
        if decision.entry is None or not validate_pending_entry(
            decision.order_type, decision.entry, price['ask'], price['bid']
        ):
            return {'status': 'rejected', 'reason': f"Entry price invalid for {decision.order_type}"}

    entry_price = decision.entry or (price['ask'] if 'BUY' in decision.order_type else price['bid'])
    sl_distance = abs(entry_price - decision.stop_loss) if decision.stop_loss else 0

    volume = calculate_lot(
        account_balance=account['balance'],
        risk_pct=risk_config['risk_per_trade_pct'],
        sl_distance=sl_distance,
        contract_size=sym_info['trade_contract_size'],
        confidence=decision.confidence,
        volume_min=sym_info['volume_min'],
        volume_max=sym_info['volume_max'],
        volume_step=sym_info['volume_step'],
        max_lot_cap_pct=risk_config['max_lot_hard_cap_pct'],
    )

    try:
        if decision.order_type in ('BUY', 'SELL'):
            result = client.place_market_order(
                symbol=symbol, order_type=decision.order_type,
                volume=volume, sl=decision.stop_loss, tp=decision.take_profit,
            )
        else:
            result = client.place_pending_order(
                symbol=symbol, order_type=decision.order_type, volume=volume,
                entry=decision.entry, sl=decision.stop_loss, tp=decision.take_profit,
                expiry_hours=decision.expiry_hours or 4.0,
            )
        return {'status': 'executed', 'order_id': result.get('order_id'), 'volume': volume}
    except ValueError as e:
        return {'status': 'failed', 'reason': str(e)}
