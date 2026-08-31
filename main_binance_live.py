"""Live runner that connects strategy to Binance via OrderManager.

Usage: set ENV variables (API keys) and run python main_binance_live.py
Use config.yaml to change symbol/interval/params. Default runs with dry_run=true.
"""
import logging
import yaml
import os
import asyncio

from dotenv import load_dotenv
from exchangers.binance_client import BinanceClient
from order_manager import OrderManager
from binance_ws import BinanceWS
from strategy import SimpleStrategy


def load_config(path: str = "config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


async def on_ws_message(raw_msg, client: BinanceClient, om: OrderManager, strat: SimpleStrategy, cfg: dict):
    k = raw_msg.get("k")
    if not k:
        return
    is_closed = k.get("x", False)
    close = float(k.get("c"))
    if is_closed:
        action = strat.on_candle_close(close)
        if action["action"] == "buy":
            # compute account balance in quote asset (e.g., USDT)
            quote_asset = cfg.get("quote_asset", "USDT")
            balance = client.get_balance(quote_asset) or cfg.get("starting_balance", 0)
            price = action["price"]
            qty = om.compute_qty(price, balance, cfg.get("risk_per_trade", 0.01), cfg.get("stop_pct", 0.02))
            if qty > 0:
                res = om.place_buy(cfg.get("symbol", "BTCUSDT"), price, balance, cfg.get("risk_per_trade", 0.01), cfg.get("stop_pct", 0.02))
                logging.info("Buy result: %s", res)
        elif action["action"] == "sell":
            # sell full position via client.position (we rely on order history)
            # naive: compute qty from last buy
            last_buy = None
            for h in reversed(om.order_history):
                if h.get("side") == "buy":
                    last_buy = h
                    break
            if last_buy:
                qty = last_buy.get("qty", 0)
                res = om.place_sell(cfg.get("symbol", "BTCUSDT"), action["price"], qty)
                logging.info("Sell result: %s", res)


def run(config_path: str = "config.yaml"):
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    cfg = load_config(config_path)

    use_testnet = cfg.get("use_testnet", True)
    dry_run = cfg.get("dry_run", True)
    symbol = cfg.get("symbol", "BTCUSDT")
    interval = cfg.get("interval", "1m")

    client = BinanceClient(use_testnet=use_testnet, dry_run=dry_run)
    om = OrderManager(client, max_exposure_per_trade=cfg.get("max_exposure_per_trade", 0.05), max_trades_per_day=cfg.get("max_trades_per_day", 10), dry_run=dry_run)
    strat = SimpleStrategy(target_pct=cfg.get("target_pct", 0.05), stop_pct=cfg.get("stop_pct", 0.02), risk_per_trade=cfg.get("risk_per_trade", 0.01))

    ws = BinanceWS(symbol=symbol, interval=interval, use_testnet=use_testnet)

    async def _on_message(msg):
        await on_ws_message(msg, client, om, strat, cfg)

    try:
        ws.run(_on_message)
    except Exception:
        logging.exception("Runtime error")
    finally:
        logging.info("Order history: %s", om.order_history)


if __name__ == "__main__":
    run()
