"""Order manager: safety checks, sizing and order execution with retries and dry-run support."""
import logging
import time
from datetime import date
from typing import Dict, Optional


class OrderManager:
    def __init__(self, client, max_exposure_per_trade: float = 0.05, max_trades_per_day: int = 10, dry_run: bool = True):
        self.client = client
        self.max_exposure_per_trade = max_exposure_per_trade
        self.max_trades_per_day = max_trades_per_day
        self.dry_run = dry_run or getattr(client, "dry_run", True)
        self._trades_today = 0
        self._trades_date = date.today()
        self.order_history = []

    def _reset_daily_counts(self):
        today = date.today()
        if today != self._trades_date:
            self._trades_date = today
            self._trades_today = 0

    def can_trade(self):
        self._reset_daily_counts()
        if self._trades_today >= self.max_trades_per_day:
            logging.warning("Max trades per day reached: %d", self._trades_today)
            return False
        return True

    def compute_qty(self, price: float, account_balance: float, risk_per_trade: float, stop_pct: float) -> float:
        """Simple sizing: qty = (balance * risk) / (price * stop_pct), then cap by max_exposure_per_trade."""
        if stop_pct <= 0 or price <= 0:
            logging.warning("Invalid stop_pct or price for sizing")
            return 0.0
        nominal = (account_balance * risk_per_trade) / (price * stop_pct)
        # cap exposure converted to qty
        max_exposure_value = account_balance * self.max_exposure_per_trade
        max_qty = max_exposure_value / price if price > 0 else 0
        qty = min(nominal, max_qty)
        return max(0.0, qty)

    def place_buy(self, symbol: str, price: float, account_balance: float, risk_per_trade: float, stop_pct: float, max_retries: int = 3):
        if not self.can_trade():
            return {"status": "blocked"}
        qty = self.compute_qty(price, account_balance, risk_per_trade, stop_pct)
        if qty <= 0:
            logging.warning("Computed qty is 0, skipping buy")
            return {"status": "zero_qty"}

        attempt = 0
        while attempt < max_retries:
            attempt += 1
            res = self.client.place_market_order("BUY", symbol, qty)
            if res and res.get("status") != "ERROR":
                self._trades_today += 1
                rec = {"side": "buy", "symbol": symbol, "qty": qty, "price": price, "time": time.time(), "result": res}
                self.order_history.append(rec)
                return {"status": "ok", "order": rec}
            logging.warning("Buy attempt %d failed, retrying...", attempt)
            time.sleep(1 * attempt)
        return {"status": "failed"}

    def place_sell(self, symbol: str, price: float, qty: float, max_retries: int = 3):
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            res = self.client.place_market_order("SELL", symbol, qty)
            if res and res.get("status") != "ERROR":
                rec = {"side": "sell", "symbol": symbol, "qty": qty, "price": price, "time": time.time(), "result": res}
                self.order_history.append(rec)
                return {"status": "ok", "order": rec}
            logging.warning("Sell attempt %d failed, retrying...", attempt)
            time.sleep(1 * attempt)
        return {"status": "failed"}
