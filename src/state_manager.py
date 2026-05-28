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


def update_symbol_state(symbol: str, decision: dict, m15_candle_time: str, result: dict):
    state = load_state()
    state['symbols'][symbol] = {
        'last_signal': decision,
        'm15_candle_time': m15_candle_time,
        'last_result': result,
        'updated_at': datetime.now().isoformat(),
    }
    state['last_cycle'] = datetime.now().isoformat()
    save_state(state)


def get_last_m15_candle_time(symbol: str) -> Optional[str]:
    state = load_state()
    return state.get('symbols', {}).get(symbol, {}).get('m15_candle_time')
