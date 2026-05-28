import re
from dataclasses import dataclass
from typing import Optional

VALID_ORDER_TYPES = {'BUY', 'BUY LIMIT', 'BUY STOP', 'SELL', 'SELL LIMIT', 'SELL STOP', 'HOLD'}
VALID_CONFIDENCE = {'HIGH', 'MEDIUM', 'LOW'}


@dataclass
class TradeDecision:
    order_type: str
    entry: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: str
    expiry_hours: Optional[float]
    reason: str


def parse_response(raw: str) -> TradeDecision:
    try:
        return _parse(raw)
    except (ValueError, KeyError, AttributeError, StopIteration) as e:
        return TradeDecision(
            order_type='HOLD',
            entry=None, stop_loss=None, take_profit=None,
            confidence='LOW', expiry_hours=None,
            reason=f'Parse error: {e}',
        )


def _extract(field: str, raw: str) -> str:
    match = re.search(rf'^{field}:\s*(.+)$', raw, re.MULTILINE)
    if not match:
        raise ValueError(f'Missing field: {field}')
    return match.group(1).strip()


def _parse_float_or_none(field: str, raw: str) -> Optional[float]:
    val = _extract(field, raw)
    return None if val.upper() == 'N/A' else float(val)


def _parse_expiry(raw: str) -> Optional[float]:
    val = _extract('EXPIRY', raw).upper()
    if val == 'N/A':
        return None
    match = re.match(r'^(\d+(?:\.\d+)?)H$', val)
    if not match:
        raise ValueError(f'Invalid EXPIRY format: {val}')
    return float(match.group(1))


def _parse(raw: str) -> TradeDecision:
    order_type = _extract('ORDER_TYPE', raw).upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(f'Invalid ORDER_TYPE: {order_type}')

    confidence = _extract('CONFIDENCE', raw).upper()
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(f'Invalid CONFIDENCE: {confidence}')

    reason = _extract('REASON', raw)

    if order_type == 'HOLD':
        return TradeDecision(
            order_type='HOLD',
            entry=None, stop_loss=None, take_profit=None,
            confidence=confidence, expiry_hours=None,
            reason=reason,
        )

    return TradeDecision(
        order_type=order_type,
        entry=_parse_float_or_none('ENTRY', raw),
        stop_loss=_parse_float_or_none('STOP_LOSS', raw),
        take_profit=_parse_float_or_none('TAKE_PROFIT', raw),
        confidence=confidence,
        expiry_hours=_parse_expiry(raw),
        reason=reason,
    )
