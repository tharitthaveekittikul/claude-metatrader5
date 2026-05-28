import json
import os
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import streamlit as st
import yaml

st.set_page_config(page_title='Claude MT5 Bot', page_icon='📈', layout='wide')

# ── CSS: only badges (outlined — work in light + dark) ───────────────────────
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.03em;
    white-space: nowrap;
    border: 1.5px solid;
}
.b-buy     { color: #16a34a; border-color: #16a34a; }
.b-sell    { color: #dc2626; border-color: #dc2626; }
.b-pending { color: #2563eb; border-color: #2563eb; }
.b-hold    { color: #6b7280; border-color: #6b7280; }
.b-high    { color: #16a34a; border-color: #16a34a; }
.b-medium  { color: #d97706; border-color: #d97706; }
.b-low     { color: #dc2626; border-color: #dc2626; }
.b-ok      { color: #16a34a; border-color: #16a34a; }
.b-reject  { color: #dc2626; border-color: #dc2626; }
.b-neutral { color: #6b7280; border-color: #6b7280; }

.sig-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.sig-table th {
    text-align: left;
    padding: 8px 14px;
    border-bottom: 2px solid rgba(128,128,128,0.2);
    color: #6b7280;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.sig-table td {
    padding: 10px 14px;
    border-bottom: 1px solid rgba(128,128,128,0.1);
}
</style>
""", unsafe_allow_html=True)


# ── Data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_state() -> dict:
    if not os.path.exists('state.json'):
        return {'symbols': {}, 'last_cycle': None}
    with open('state.json') as f:
        return json.load(f)


@st.cache_data(ttl=30)
def load_config() -> dict:
    with open('config.yaml') as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    load_config.clear()
    load_state.clear()
    load_broker_symbols.clear()


@st.cache_data(ttl=300)
def load_broker_symbols() -> list:
    cfg = load_config()['mt5']
    kwargs = {'login': cfg['login'], 'password': cfg['password'], 'server': cfg['server']}
    if 'path' in cfg:
        kwargs['path'] = cfg['path']
    if not mt5.initialize(**kwargs):
        return []
    try:
        symbols = mt5.symbols_get()
        return sorted([s.name for s in symbols]) if symbols else []
    finally:
        mt5.shutdown()


def get_next_trigger() -> datetime:
    now = datetime.now()
    for minute in [0, 15, 30, 45]:
        candidate = now.replace(minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
    return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


# ── Badge helpers ─────────────────────────────────────────────────────────────
def badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def decision_badge(val: str) -> str:
    v = str(val).upper()
    if v == 'BUY':            return badge(v, 'b-buy')
    if v == 'SELL':           return badge(v, 'b-sell')
    if v in ('BUY LIMIT', 'BUY STOP', 'SELL LIMIT', 'SELL STOP'):
                              return badge(v, 'b-pending')
    if v == 'HOLD':           return badge(v, 'b-hold')
    return badge(v, 'b-neutral')


def confidence_badge(val: str) -> str:
    cls = {'HIGH': 'b-high', 'MEDIUM': 'b-medium', 'LOW': 'b-low'}.get(str(val).upper(), 'b-neutral')
    return badge(val, cls)


def execution_badge(val: str) -> str:
    lower = str(val).lower()
    if any(k in lower for k in ('filled', 'done', 'placed')):  return badge(val, 'b-ok')
    if any(k in lower for k in ('reject', 'error', 'fail')):   return badge(val, 'b-reject')
    return badge(val, 'b-neutral')


# ── Load data ─────────────────────────────────────────────────────────────────
state  = load_state()
config = load_config()
mode   = config['mt5']['mode'].upper()

# ── Header ────────────────────────────────────────────────────────────────────
st.title('📈 Claude MT5 Trading Bot')

next_trigger = get_next_trigger()
remaining    = next_trigger - datetime.now()
mins = int(remaining.seconds // 60)
secs = int(remaining.seconds % 60)
last_cycle = state.get('last_cycle')

col1, col2, col3, col4 = st.columns(4)
col1.metric('⏱ Next Trigger In', f'{mins}m {secs}s')
col2.metric('Mode', mode)
col3.metric('Assets Configured', len(config['assets']))
col4.metric('Last Cycle', str(last_cycle)[:16] if last_cycle else 'Never')

st.divider()

# ── Asset Manager ─────────────────────────────────────────────────────────────
st.subheader('Asset Manager')
assets: list = config['assets'].copy()

broker_symbols = load_broker_symbols()
col_input, col_btn = st.columns([3, 1], vertical_alignment='bottom')
if broker_symbols:
    choices  = [s for s in broker_symbols if s not in assets]
    selected = col_input.selectbox('Select symbol to add', ['— select —'] + choices, key='new_asset_select')
    if col_btn.button('Add Symbol', use_container_width=True) and selected != '— select —':
        assets.append(selected)
        config['assets'] = assets
        save_config(config)
        st.rerun()
else:
    new_asset = col_input.text_input('Symbol to add (MT5 offline — type manually)', key='new_asset_input')
    if col_btn.button('Add Symbol', use_container_width=True) and new_asset.strip():
        symbol = new_asset.strip().upper()
        if symbol not in assets:
            assets.append(symbol)
            config['assets'] = assets
            save_config(config)
            st.rerun()

if assets:
    for asset in assets:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'**{asset}**')
        if c2.button('Remove', key=f'remove_{asset}'):
            assets.remove(asset)
            config['assets'] = assets
            save_config(config)
            st.rerun()
else:
    st.caption('No assets configured.')

st.divider()

# ── Last Signals ──────────────────────────────────────────────────────────────
st.subheader('Last Signals')
symbols_state = state.get('symbols', {})
if symbols_state:
    rows_html = []
    for sym, data in symbols_state.items():
        sig    = data.get('last_signal', {})
        result = data.get('last_result', {})
        entry  = sig.get('entry')
        sl     = sig.get('stop_loss')
        tp     = sig.get('take_profit')
        rows_html.append(f"""
        <tr>
          <td><strong>{sym}</strong></td>
          <td>{decision_badge(sig.get('order_type', '—'))}</td>
          <td>{confidence_badge(sig.get('confidence', '—'))}</td>
          <td>{f'{entry:.5f}' if isinstance(entry, float) else 'N/A'}</td>
          <td>{f'{sl:.5f}'    if isinstance(sl,    float) else 'N/A'}</td>
          <td>{f'{tp:.5f}'    if isinstance(tp,    float) else 'N/A'}</td>
          <td>{execution_badge(result.get('status', '—'))}</td>
          <td style="color:#9ca3af">{str(data.get('updated_at', '—'))[:16]}</td>
        </tr>""")

    st.markdown(f"""
    <table class="sig-table">
      <thead><tr>
        <th>Symbol</th><th>Decision</th><th>Confidence</th>
        <th>Entry</th><th>SL</th><th>TP</th>
        <th>Execution</th><th>Updated</th>
      </tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>""", unsafe_allow_html=True)
else:
    st.info('No signals yet — waiting for first cycle.')

st.divider()

# ── Trade Log — st.code() has built-in copy button, works in light + dark ────
st.subheader('Trade Log (last 40 lines)')
try:
    with open('logs/trades.log') as f:
        lines = f.readlines()[-40:]
    st.code(''.join(lines), language='text')
except FileNotFoundError:
    st.info('No trade log yet — appears after first cycle.')

time.sleep(1)
st.rerun()
