# Simple paper market engine to execute market buy/sell orders and track balance/positions
# This is a naive simulator for spot trading (no leverage), intended for paper testing only.

import logging
from typing import Optional, Dict


class PaperEngine:
    def __init__(self, starting_balance: float = 10000.0):
        self.balance = starting_balance  # quote currency balance (e.g., USDT)
        self.position: Optional[Dict] = None  # {"qty": float, "entry_price": float}
        self.trade_history = []

    def buy_market(self, price: float, qty: float):
        cost = price * qty
        if cost > self.balance:
            logging.warning("Not enough balance to buy: needed %.2f have %.2f", cost, self.balance)
            return False
        self.balance -= cost
        self.position = {"qty": qty, "entry_price": price}
        self.trade_history.append({"side": "buy", "price": price, "qty": qty})
        logging.info("Paper BUY qty=%.6f @ %.2f | remaining balance=%.2f", qty, price, self.balance)
        return True

    def sell_market(self, price: float):
        if not self.position:
            logging.warning("No position to sell")
            return False
        qty = self.position["qty"]
        proceeds = price * qty
        self.balance += proceeds
        self.trade_history.append({"side": "sell", "price": price, "qty": qty})
        logging.info("Paper SELL qty=%.6f @ %.2f | new balance=%.2f", qty, price, self.balance)
        self.position = None
        return True

    def position_value(self, price: float) -> float:
        if not self.position:
            return 0.0
        return self.position["qty"] * price

    def get_equity(self, price: float) -> float:
        # equity = balance (quote) + position value
        return self.balance + self.position_value(price)
