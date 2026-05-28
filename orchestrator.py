import logging
import os
import signal
import time
import yaml
import MetaTrader5 as mt5
from apscheduler.schedulers.background import BackgroundScheduler

from src.mt5_client import MT5Client
from src.indicators import calculate_indicators, determine_trend_bias
from src.prompt_builder import build_prompt
from src.claude_caller import call_claude
from src.response_parser import parse_response
from src.order_executor import execute_order
from src import state_manager

os.makedirs('logs', exist_ok=True)

_fmt = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=_fmt,
    handlers=[
        logging.FileHandler('logs/trades.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_config(path: str = 'config.yaml') -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_symbol(symbol: str, client: MT5Client, config: dict):
    try:
        h1_cfg = config['indicators']['h1']
        m15_cfg = config['indicators']['m15']

        h1_candles = client.get_candles(symbol, mt5.TIMEFRAME_H1, h1_cfg['candles_lookback'])
        m15_candles = client.get_candles(symbol, mt5.TIMEFRAME_M15, m15_cfg['candles_lookback'])

        current_m15_time = str(m15_candles.iloc[-1]['time'])
        if state_manager.get_last_m15_candle_time(symbol) == current_m15_time:
            logger.info(f"{symbol}: skipping duplicate M15 candle {current_m15_time}")
            return

        h1_ind = calculate_indicators(
            h1_candles, h1_cfg['ma_periods'], h1_cfg['rsi_period'],
            h1_cfg['atr_period'], h1_cfg['bollinger'],
        )
        m15_ind = calculate_indicators(
            m15_candles, m15_cfg['ma_periods'], m15_cfg['rsi_period'],
            m15_cfg['atr_period'], m15_cfg['bollinger'],
        )

        price = client.get_symbol_price(symbol)
        trend_bias = determine_trend_bias(h1_ind, price['ask'])
        account = client.get_account_info()
        all_positions = client.get_open_positions()
        account['total_positions'] = len(all_positions)
        open_pos = client.get_open_positions(symbol)
        pending = client.get_pending_orders(symbol)
        closed = client.get_closed_trades(
            symbol,
            config['trade_history']['max_trades'],
            config['trade_history']['lookback_hours'],
        )

        prompt = build_prompt(
            symbol=symbol, price=price,
            h1_indicators=h1_ind, m15_indicators=m15_ind,
            trend_bias=trend_bias, account=account,
            open_positions=open_pos, pending_orders=pending,
            closed_trades=closed, max_trades=config['trade_history']['max_trades'],
        )

        raw = call_claude(prompt, config['claude']['model'], config['claude']['timeout_seconds'])
        decision = parse_response(raw['text'])
        usage = {k: raw[k] for k in ('cost_usd', 'input_tokens', 'output_tokens')}

        logger.info(
            f"{symbol}: {decision.order_type} CONF={decision.confidence} "
            f"tokens={usage['input_tokens']}in/{usage['output_tokens']}out "
            f"cost=${usage['cost_usd']:.4f} REASON={decision.reason}"
        )

        result = execute_order(decision, symbol, client, config['risk'], account)
        logger.info(f"{symbol}: result={result}")

        state_manager.update_symbol_state(
            symbol,
            {
                'order_type': decision.order_type,
                'entry': decision.entry,
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'confidence': decision.confidence,
                'expiry': decision.expiry_hours,
                'reason': decision.reason,
            },
            current_m15_time,
            result,
            usage,
            prompt=prompt,
            response=raw['text'],
        )

    except Exception as e:
        logger.error(f"{symbol}: cycle error — {e}", exc_info=True)


def run_cycle():
    config = load_config()
    client = MT5Client(config)

    if not client.connect():
        logger.error("MT5 connection failed — is MetaTrader 5 terminal running?")
        return

    try:
        for symbol in config['assets']:
            logger.info(f"Processing {symbol}")
            run_symbol(symbol, client, config)
    finally:
        client.disconnect()


def startup_check():
    config = load_config()
    client = MT5Client(config)
    if not client.connect():
        logger.error("Startup MT5 connection FAILED — is MetaTrader 5 terminal open and logged in?")
        return False
    try:
        import MetaTrader5 as _mt5
        info = _mt5.account_info()
        logger.info("=" * 50)
        logger.info("MT5 Connected successfully")
        logger.info(f"  Account : {info.login}")
        logger.info(f"  Name    : {info.name}")
        logger.info(f"  Server  : {info.server}")
        logger.info(f"  Mode    : {config['mt5']['mode'].upper()}")
        logger.info(f"  Balance : {info.balance} {info.currency}")
        logger.info(f"  Equity  : {info.equity} {info.currency}")
        logger.info(f"  Assets  : {config['assets']}")
        logger.info("=" * 50)
    finally:
        client.disconnect()
    return True


def main():
    signal.signal(signal.SIGINT, signal.default_int_handler)
    logger.info("Orchestrator starting")
    if not startup_check():
        return
    scheduler = BackgroundScheduler(timezone='UTC')
    scheduler.add_job(run_cycle, 'cron', minute='0,15,30,45')
    scheduler.start()
    logger.info("Scheduler running — waiting for next :00/:15/:30/:45")
    logger.info("Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Orchestrator stopped by user")
        scheduler.shutdown(wait=False)


if __name__ == '__main__':
    main()
