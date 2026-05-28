import json
import os
from datetime import datetime
from typing import Optional

STATE_FILE = 'state.json'


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {'symbols': {}, 'last_cycle': None}
    with open(STATE_FILE, 'r') as f:
        return json.load(f)


def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def update_symbol_state(
    symbol: str, decision: dict, m15_candle_time: str, result: dict,
    usage: dict = None, prompt: str = None, response: str = None,
):
    state = load_state()
    now = datetime.now().isoformat()
    state['symbols'][symbol] = {
        'last_signal': decision,
        'm15_candle_time': m15_candle_time,
        'last_result': result,
        'last_usage': usage or {},
        'last_prompt': prompt or '',
        'last_response': response or '',
        'updated_at': now,
    }
    if usage:
        totals = state.get('totals', {})
        totals.setdefault('cost_usd', 0.0)
        totals.setdefault('input_tokens', 0)
        totals.setdefault('cache_read_tokens', 0)
        totals.setdefault('cache_creation_tokens', 0)
        totals.setdefault('output_tokens', 0)
        totals.setdefault('calls', 0)
        totals['cost_usd']              += usage.get('cost_usd', 0.0)
        totals['input_tokens']          += usage.get('input_tokens', 0)
        totals['cache_read_tokens']     += usage.get('cache_read_tokens', 0)
        totals['cache_creation_tokens'] += usage.get('cache_creation_tokens', 0)
        totals['output_tokens']         += usage.get('output_tokens', 0)
        totals['calls']                 += 1
        state['totals'] = totals
        history = state.get('call_history', [])
        history.append({
            'time': now,
            'symbol': symbol,
            'decision': decision.get('order_type', ''),
            'confidence': decision.get('confidence', ''),
            'cost_usd': usage.get('cost_usd', 0.0),
            'input_tokens': usage.get('input_tokens', 0),
            'cache_read_tokens': usage.get('cache_read_tokens', 0),
            'cache_creation_tokens': usage.get('cache_creation_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'status': result.get('status', ''),
        })
        state['call_history'] = history[-200:]
    state['last_cycle'] = now
    save_state(state)


def get_last_m15_candle_time(symbol: str) -> Optional[str]:
    state = load_state()
    return state.get('symbols', {}).get(symbol, {}).get('m15_candle_time')
