import json
import os
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import streamlit as st
import yaml

from orchestrator import run_cycle

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

totals = state.get('totals', {})
total_cost = totals.get('cost_usd', 0.0)
total_calls = totals.get('calls', 0)
call_history = state.get('call_history', [])

col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
col1.metric('⏱ Next Trigger In', f'{mins}m {secs}s')
col2.metric('Mode', mode)
col3.metric('Assets', len(config['assets']))
col4.metric('Last Cycle', str(last_cycle)[:16] if last_cycle else 'Never')
col_cost, col_hist, col_run = st.columns([1, 3, 1])
col_cost.metric('Total API Cost', f'${total_cost:.4f}', f'{total_calls} calls')
if col_run.button('▶ Run Now', use_container_width=True, type='primary'):
    with st.spinner('Running cycle — this may take ~30s…'):
        run_cycle()
    load_state.clear()
    st.rerun()
if call_history:
    with col_hist.expander(f'View all {total_calls} calls'):
        hist_rows = []
        for c in reversed(call_history[-100:]):
            hist_rows.append(f"""<tr>
              <td style="color:#9ca3af">{c['time'][:16]}</td>
              <td><strong>{c['symbol']}</strong></td>
              <td>{decision_badge(c['decision'])}</td>
              <td>{confidence_badge(c.get('confidence','—'))}</td>
              <td>{execution_badge(c['status'])}</td>
              <td>${c['cost_usd']:.4f}</td>
              <td style="color:#9ca3af">{c['input_tokens']}in/{c['output_tokens']}out</td>
            </tr>""")
        st.markdown(f"""<table class="sig-table">
          <thead><tr>
            <th>Time</th><th>Symbol</th><th>Decision</th><th>Conf</th>
            <th>Status</th><th>Cost</th><th>Tokens</th>
          </tr></thead>
          <tbody>{''.join(hist_rows)}</tbody>
        </table>""", unsafe_allow_html=True)


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

if 'pending_remove' not in st.session_state:
    st.session_state.pending_remove = None

if assets:
    for asset in assets:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'**{asset}**')
        if c2.button('Remove', key=f'remove_{asset}'):
            st.session_state.pending_remove = asset

    if st.session_state.pending_remove:
        asset = st.session_state.pending_remove
        st.warning(f'Remove **{asset}** from trading? This stops it from being analysed next cycle.')
        cc1, cc2, _ = st.columns([1, 1, 5])
        if cc1.button('Yes, Remove', type='primary', key='confirm_remove'):
            assets.remove(asset)
            config['assets'] = assets
            save_config(config)
            st.session_state.pending_remove = None
            st.rerun()
        if cc2.button('Cancel', key='cancel_remove'):
            st.session_state.pending_remove = None
            st.rerun()
else:
    st.caption('No assets configured.')

st.divider()

# ── Last Signals ──────────────────────────────────────────────────────────────
st.subheader('Last Signals')
symbols_state = state.get('symbols', {})

HDR = ['SYMBOL', 'DECISION', 'CONF', 'ENTRY', 'SL', 'TP', 'EXECUTION', 'COST', 'UPDATED']
COLS = [2, 2, 1.5, 1.5, 1.5, 1.5, 1.5, 2, 2]

if symbols_state:
    hcols = st.columns(COLS)
    for col, lbl in zip(hcols, HDR):
        col.markdown(
            f'<span style="font-size:11px;font-weight:700;color:#6b7280;'
            f'letter-spacing:.07em">{lbl}</span>',
            unsafe_allow_html=True,
        )
    st.markdown('<hr style="margin:4px 0;border-color:rgba(128,128,128,.2)">', unsafe_allow_html=True)

    for sym, data in symbols_state.items():
        sig     = data.get('last_signal', {})
        result  = data.get('last_result', {})
        usage   = data.get('last_usage', {})
        entry   = sig.get('entry')
        sl      = sig.get('stop_loss')
        tp      = sig.get('take_profit')
        cost    = usage.get('cost_usd')
        tok_in  = usage.get('input_tokens', 0)
        tok_out = usage.get('output_tokens', 0)

        row = st.columns(COLS)
        row[0].markdown(f'**{sym}**')
        row[1].markdown(decision_badge(sig.get('order_type', '—')), unsafe_allow_html=True)
        row[2].markdown(confidence_badge(sig.get('confidence', '—')), unsafe_allow_html=True)
        row[3].write(f'{entry:.5f}' if isinstance(entry, float) else 'N/A')
        row[4].write(f'{sl:.5f}'    if isinstance(sl,    float) else 'N/A')
        row[5].write(f'{tp:.5f}'    if isinstance(tp,    float) else 'N/A')
        row[6].markdown(execution_badge(result.get('status', '—')), unsafe_allow_html=True)
        if cost is not None:
            row[7].markdown(
                f'`${cost:.4f}`<br><span style="font-size:11px;color:#9ca3af">'
                f'{tok_in}in/{tok_out}out</span>',
                unsafe_allow_html=True,
            )
        else:
            row[7].write('—')
        row[8].markdown(
            f'<span style="color:#9ca3af">{str(data.get("updated_at","—"))[:16]}</span>',
            unsafe_allow_html=True,
        )

        with st.expander(f'Details — {sym}'):
            last_prompt   = data.get('last_prompt', '')
            last_response = data.get('last_response', '')
            reason = sig.get('reason', '')
            if reason:
                st.markdown(f'**Reason:** {reason}')
            tab_in, tab_out = st.tabs(['Prompt (input)', 'Response (output)'])
            with tab_in:
                st.code(last_prompt or 'Not captured yet — restart bot', language='text')
            with tab_out:
                st.code(last_response or 'Not captured yet — restart bot', language='text')

        st.markdown('<hr style="margin:2px 0;border-color:rgba(128,128,128,.08)">', unsafe_allow_html=True)
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
