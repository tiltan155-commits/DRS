# Main orchestrator for paper Binance streaming strategy

import logging
import yaml
import time
import asyncio
from decimal import Decimal

from binance_ws import BinanceWS
from paper_engine import PaperEngine
from strategy import SimpleStrategy


def load_config(path: str = "config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


async def on_ws_message(raw_msg, paper, strat):
    # raw_msg is the JSON kline payload from Binance
    # structure: {"k": {"t":..., "T":..., "s":"BTCUSDT", "k":..., "x":<is_closed>, ...}}
    k = raw_msg.get("k")
    if not k:
        return
    is_closed = k.get("x", False)
    close = float(k.get("c"))
    if is_closed:
        # candle closed, pass to strategy
        action = strat.on_candle_close(close)
        if action["action"] == "buy":
            # compute qty using risk sizing (naive): qty = (balance * risk) / (price * stop_pct)
            price = action["price"]
            stop_pct = strat.stop_pct if hasattr(strat, "stop_pct") else strat.stop_pct if hasattr(strat, "stop_pct") else 0.02
            risk = strat.risk_per_trade
            # protect division by zero
            if stop_pct <= 0:
                logging.warning("Invalid stop_pct for sizing, defaulting to 0.02")
                stop_pct = 0.02
            qty = (paper.balance * risk) / (price * stop_pct)
            if qty <= 0:
                logging.warning("Calculated zero qty, skipping buy")
            else:
                paper.buy_market(price, qty)
        elif action["action"] == "sell":
            # market sell full position
            paper.sell_market(action["price"])


def run(config_path: str = "config.yaml"):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    cfg = load_config(config_path)
    symbol = cfg.get("symbol", "BTCUSDT")
    interval = cfg.get("interval", "1m")
    use_testnet = cfg.get("use_testnet", True)

    paper = PaperEngine(starting_balance=cfg.get("starting_balance", 10000.0))
    strat = SimpleStrategy(target_pct=cfg.get("target_pct", 0.05), stop_pct=cfg.get("stop_pct", 0.02), risk_per_trade=cfg.get("risk_per_trade", 0.01))

    ws = BinanceWS(symbol=symbol, interval=interval, use_testnet=use_testnet)

    async def _on_message(msg):
        await on_ws_message(msg, paper, strat)

    # run websocket in asyncio
    try:
        ws.run(_on_message)
    except Exception:
        logging.exception("Runner error")
    finally:
        # print final summary
        logging.info("Final balance: %.2f", paper.balance)
        logging.info("Trades:")
        for t in paper.trade_history:
            logging.info(t)


if __name__ == "__main__":
    run()
