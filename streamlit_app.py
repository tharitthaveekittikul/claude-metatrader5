import json
import os
from datetime import datetime, timedelta

import streamlit as st
import yaml

st.set_page_config(page_title='Claude MT5 Bot', layout='wide')
st.title('Claude MT5 Trading Bot')


def load_state() -> dict:
    if not os.path.exists('state.json'):
        return {'symbols': {}, 'last_cycle': None}
    with open('state.json') as f:
        return json.load(f)


def load_config() -> dict:
    with open('config.yaml') as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def get_next_trigger() -> datetime:
    now = datetime.now()
    for minute in [0, 15, 30, 45]:
        candidate = now.replace(minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
    return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


state = load_state()
config = load_config()

# ── Top metrics ──────────────────────────────────────────────────────────────
next_trigger = get_next_trigger()
remaining = next_trigger - datetime.now()
mins = int(remaining.seconds // 60)
secs = int(remaining.seconds % 60)

col1, col2, col3, col4 = st.columns(4)
col1.metric('Next Trigger In', f'{mins}m {secs}s')
col2.metric('Mode', config['mt5']['mode'].upper())
col3.metric('Assets Configured', len(config['assets']))
last_cycle = state.get('last_cycle', 'Never')
col4.metric('Last Cycle', str(last_cycle)[:16] if last_cycle else 'Never')

st.divider()

# ── Asset Manager ─────────────────────────────────────────────────────────────
st.subheader('Asset Manager')
assets: list = config['assets'].copy()

col_input, col_btn = st.columns([3, 1])
new_asset = col_input.text_input('Symbol to add (e.g. EURUSD)', key='new_asset_input')
if col_btn.button('Add', use_container_width=True) and new_asset.strip():
    symbol = new_asset.strip().upper()
    if symbol not in assets:
        assets.append(symbol)
        config['assets'] = assets
        save_config(config)
        st.rerun()

for asset in assets:
    c1, c2 = st.columns([5, 1])
    c1.write(f'**{asset}**')
    if c2.button('Remove', key=f'remove_{asset}'):
        assets.remove(asset)
        config['assets'] = assets
        save_config(config)
        st.rerun()

st.divider()

# ── Last Signals ──────────────────────────────────────────────────────────────
st.subheader('Last Signals')
symbols_state = state.get('symbols', {})
if symbols_state:
    rows = []
    for sym, data in symbols_state.items():
        sig = data.get('last_signal', {})
        result = data.get('last_result', {})
        rows.append({
            'Symbol': sym,
            'Decision': sig.get('order_type', '-'),
            'Confidence': sig.get('confidence', '-'),
            'Entry': sig.get('entry') or 'N/A',
            'SL': sig.get('stop_loss') or 'N/A',
            'TP': sig.get('take_profit') or 'N/A',
            'Execution': result.get('status', '-'),
            'Updated': str(data.get('updated_at', '-'))[:16],
        })
    st.dataframe(rows, use_container_width=True)
else:
    st.info('No signals yet — waiting for first cycle.')

st.divider()

# ── Trade Log ─────────────────────────────────────────────────────────────────
st.subheader('Trade Log (last 30 lines)')
try:
    with open('logs/trades.log') as f:
        lines = f.readlines()[-30:]
    st.code(''.join(lines), language='text')
except FileNotFoundError:
    st.info('No trade log yet — log appears after first cycle.')

# Auto-refresh every 10 seconds
st.markdown(
    '<meta http-equiv="refresh" content="10">',
    unsafe_allow_html=True,
)
