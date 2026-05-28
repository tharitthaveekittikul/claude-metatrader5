# src/dashboard.py
import sys
import json
import yaml
import pandas as pd
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.mt5_client import MT5Client

CONFIG_PATH = Path("config.yaml")
STATE_PATH = Path("state.json")


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"symbols": {}, "totals": {}, "call_history": []}
    with open(STATE_PATH) as f:
        return json.load(f)


def get_mt5_data(config: dict) -> dict | None:
    client = MT5Client(config)
    if not client.connect():
        return None
    try:
        return {
            "account": client.get_account_info(),
            "positions": client.get_open_positions(),
            "pending": client.get_pending_orders(),
        }
    finally:
        client.disconnect()


@st.fragment(run_every=5)
def live_section(config: dict):
    data = get_mt5_data(config)

    if data is None:
        st.error("MT5 connection failed -- make sure the MT5 terminal is open.")
        return

    # Account metrics
    acc = data["account"]
    total_pnl = sum(p["profit"] for p in data["positions"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"${acc['balance']:,.2f}")
    c2.metric("Equity", f"${acc['equity']:,.2f}")
    c3.metric("Free Margin", f"${acc['free_margin']:,.2f}")
    c4.metric("Floating PnL", f"${total_pnl:+,.2f}")

    st.divider()

    # Open positions
    st.subheader("Open Positions")
    positions = data["positions"]
    if not positions:
        st.info("No open positions")
    else:
        df = pd.DataFrame([{
            "Ticket": p["ticket"],
            "Symbol": p["symbol"],
            "Type": p["type"],
            "Volume": p["volume"],
            "Open Price": p["price_open"],
            "SL": p["sl"],
            "TP": p["tp"],
            "PnL ($)": p["profit"],
        } for p in positions])

        def _pnl_color(val):
            if val > 0:
                return "color: green; font-weight: bold"
            elif val < 0:
                return "color: red; font-weight: bold"
            return ""

        st.dataframe(
            df.style.map(_pnl_color, subset=["PnL ($)"]),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # Pending orders
    st.subheader("Pending Orders")
    pending = data["pending"]
    if not pending:
        st.info("No pending orders")
    else:
        df = pd.DataFrame([{
            "Ticket": o["ticket"],
            "Symbol": o["symbol"],
            "Type": o["type"],
            "Volume": o["volume"],
            "Entry": o["price"],
            "SL": o["sl"],
            "TP": o["tp"],
        } for o in pending])
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # Bot signals
    st.subheader("Bot Signals")
    state = load_state()
    symbols = state.get("symbols", {})
    if not symbols:
        st.warning("No bot signals yet -- state.json is empty or missing.")
    else:
        rows = []
        for sym, sym_data in symbols.items():
            signal = sym_data.get("last_signal", {})
            result = sym_data.get("last_result", {})
            rows.append({
                "Symbol": sym,
                "Decision": signal.get("order_type", "-"),
                "Confidence": signal.get("confidence", "-"),
                "Status": result.get("status", "-"),
                "Updated": sym_data.get("updated_at", "-")[:19],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def static_section(state: dict):
    st.divider()
    totals = state.get("totals", {})
    history = state.get("call_history", [])

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("API Cost Totals")
        st.metric("Total Calls", totals.get("calls", 0))
        st.metric("Total Cost", f"${totals.get('cost_usd', 0.0):.4f}")
        st.metric("Input Tokens", f"{totals.get('input_tokens', 0):,}")
        st.metric("Output Tokens", f"{totals.get('output_tokens', 0):,}")

    with col2:
        st.subheader("Call History (last 20)")
        if not history:
            st.info("No calls recorded yet.")
        else:
            df = pd.DataFrame(history[-20:])
            df = df[["time", "symbol", "decision", "confidence", "status", "cost_usd"]]
            df.columns = ["Time", "Symbol", "Decision", "Confidence", "Status", "Cost ($)"]
            df["Time"] = df["Time"].str[:19]
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Claude MT5", page_icon=":chart_with_upwards_trend:", layout="wide")
    st.title("Claude MT5 Dashboard")
    st.caption("Live sections refresh every 5 seconds via MT5 terminal.")

    if not CONFIG_PATH.exists():
        st.error(f"config.yaml not found. Expected at: {CONFIG_PATH.absolute()}")
        st.stop()

    config = load_config()
    state = load_state()

    live_section(config)
    static_section(state)


if __name__ == "__main__":
    main()
