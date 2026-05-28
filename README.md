# Claude MT5 Trading Bot

Automated trading bot that analyzes MetaTrader 5 assets every 15 minutes using Claude AI and executes orders based on H1+M15 technical analysis.

**Uses your Claude subscription — no API key required.**

---

## How It Works

```
Every 15 min (:00/:15/:30/:45)
    For each asset in config.yaml:
        1. Fetch H1 + M15 candles from MT5
        2. Calculate indicators (RSI, MACD, MA, ATR, Bollinger)
        3. Send context to Claude via: claude -p "..."
        4. Parse response: BUY / SELL / BUY LIMIT / SELL LIMIT / BUY STOP / SELL STOP / HOLD
        5. Execute order in MT5 with ATR-based lot sizing
        6. Update dashboard
```

---

## Prerequisites

- Windows 10/11
- MetaTrader 5 terminal installed and logged into a **demo** account
- [Claude Code CLI](https://claude.ai/code) installed and authenticated (`claude --version`)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

---

## Setup

### 1. Install uv (if not already)

```bash
pip install uv
```

### 2. Create virtual environment and install dependencies

```bash
uv venv .venv
uv pip install -r requirements.txt
```

### 3. Install MetaTrader5 Python package

```bash
uv pip install MetaTrader5
```

### 4. Configure credentials

Copy the example config and fill in your details:

```bash
copy config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
mt5:
  login: 123456789            # your MT5 demo account number
  password: "yourpassword"
  server: "BrokerName-Demo"   # exact server name shown in MT5 bottom bar
  mode: demo                  # demo | live
  path: "C:\\Program Files\\MetaTrader 5_2\\terminal64.exe"

assets:
  - XAUUSD
  - BTCUSD
```

> `config.yaml` is gitignored — never commit credentials.

### 5. Enable algo trading in MT5

Open MetaTrader 5 → **Tools → Options → Expert Advisors**:
- ✅ Allow algorithmic trading
- ✅ Allow DLL imports

### 6. Test MT5 connection

```bash
uv run python -c "
import yaml, MetaTrader5 as mt5
cfg = yaml.safe_load(open('config.yaml'))['mt5']
ok = mt5.initialize(path=cfg.get('path',''), login=cfg['login'], password=cfg['password'], server=cfg['server'])
print('Connected:', ok)
if ok: print(mt5.account_info())
mt5.shutdown()
"
```

Expected: `Connected: True AccountInfo(...balance=...)`

---

## Running

Open **two terminals** in the project directory:

**Terminal 1 — Orchestrator (trading engine)**
```bash
uv run python orchestrator.py
```

**Terminal 2 — Dashboard (monitoring)**
```bash
uv run streamlit run streamlit_app.py
```

Dashboard opens at: `http://localhost:8501`

---

## Dashboard

| Panel | Description |
|---|---|
| **Next Trigger In** | Countdown to next analysis cycle |
| **Mode** | DEMO or LIVE |
| **Asset Manager** | Add/remove symbols (saves to config.yaml instantly) |
| **Last Signals** | Per-asset decision, confidence, entry/SL/TP, execution status |
| **Trade Log** | Last 30 lines from `logs/trades.log` |

---

## Order Types

Claude responds with one of:

| Signal | Action |
|---|---|
| `BUY` / `SELL` | Instant market order |
| `BUY LIMIT` / `SELL LIMIT` | Pending order at specified entry price |
| `BUY STOP` / `SELL STOP` | Pending order at specified entry price |
| `HOLD` | No action taken |

Pending orders include an expiry (e.g. `6h`) set by Claude.

---

## Risk Management

Configured in `config.yaml` under `risk:`:

```yaml
risk:
  risk_per_trade_pct: 1.0       # % of balance risked per trade
  confidence_lot_multiplier:
    HIGH: 1.0
    MEDIUM: 0.5
    LOW: 0.25
  max_open_positions_per_symbol: 1
  max_total_positions: 5
  max_lot_hard_cap_pct: 5.0     # hard lot cap regardless of calculation
```

Lot size = `(balance × risk%) / (SL_distance × contract_size) × confidence_multiplier`

---

## Safety Guardrails

- Duplicate order guard: rejects if same-direction position/pending already exists
- No stop-loss = order rejected
- Invalid entry price for order type = order rejected
- Parse failure = HOLD (never places unknown order)
- Per-symbol errors are caught — one failing asset doesn't stop others
- Demo/live switch: change `mode` and `server` in config only

---

## Demo → Live Transition

1. Verify consistent results on demo for ≥ 2 weeks
2. Edit `config.yaml`:
   ```yaml
   mt5:
     server: "BrokerName-Live"
     mode: live
   ```
3. Reduce `risk_per_trade_pct` to `0.5` initially
4. Monitor first 3 live cycles manually

---

## Project Structure

```
claude_mt5/
├── config.yaml              # credentials + settings (gitignored)
├── orchestrator.py          # scheduler + per-symbol pipeline
├── streamlit_app.py         # monitoring dashboard
├── state.json               # shared state (auto-generated)
├── logs/trades.log          # trade log (auto-generated)
├── src/
│   ├── mt5_client.py        # MT5 connection + orders
│   ├── indicators.py        # RSI, MACD, MA, ATR, Bollinger
│   ├── prompt_builder.py    # Claude prompt assembly
│   ├── claude_caller.py     # claude -p subprocess
│   ├── response_parser.py   # parse structured response
│   ├── order_executor.py    # lot sizing + order execution
│   └── state_manager.py     # state.json read/write
└── tests/                   # pytest test suite (49 tests)
```

---

## Running Tests

```bash
uv run pytest -v
```

Expected: 49 passed
