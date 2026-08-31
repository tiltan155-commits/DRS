#!/usr/bin/env python3
"""run_sim.py

Quick simulation runner that uses a simple EMA50+RSI strategy on a synthetic price series.
No API keys or network required. Use this to validate entry/exit logic locally.

Run:
  python run_sim.py

"""
import time
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def sma(prices: List[float], period: int) -> float:
    if len(prices) < period or period <= 0:
        return sum(prices) / len(prices) if prices else 0.0
    return sum(prices[-period:]) / period


def rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < 2:
        return 50.0
    gains = 0.0
    losses = 0.0
    length = min(len(prices) - 1, period)
    for i in range(length):
        change = prices[-1 - i] - prices[-2 - i]
        if change > 0:
            gains += change
        else:
            losses -= change
    if gains + losses == 0:
        return 50.0
    try:
        rs = (gains / length) / (losses / length) if losses != 0 else float('inf')
    except ZeroDivisionError:
        rs = float('inf')
    return 100 - (100 / (1 + rs))


class SimpleStrategy:
    def __init__(self, target_pct: float = 0.05, stop_pct: float = 0.02, risk_per_trade: float = 0.01):
        self.target_pct = target_pct
        self.stop_pct = stop_pct
        self.risk_per_trade = risk_per_trade
        self.prices: List[float] = []
        self.in_position = False
        self.entry_price = 0.0
        self.trades: List[Dict] = []

    def on_candle_close(self, close_price: float) -> Dict:
        self.prices.append(close_price)
        sma50 = sma(self.prices, 50)
        current_rsi = rsi(self.prices, 14)
        action = {"action": "hold", "price": close_price}

        if not self.in_position:
            if close_price > sma50 and current_rsi > 50:
                self.in_position = True
                self.entry_price = close_price
                self.trades.append({"type": "buy", "price": close_price})
                logging.info("ENTER @ %.2f | RSI=%.1f SMA50=%.2f", close_price, current_rsi, sma50)
                action = {"action": "buy", "price": close_price}
        else:
            if close_price >= self.entry_price * (1 + self.target_pct):
                self.in_position = False
                self.trades.append({"type": "sell_tp", "price": close_price})
                logging.info("TP HIT @ %.2f", close_price)
                action = {"action": "sell", "price": close_price}
            elif close_price <= self.entry_price * (1 - self.stop_pct):
                self.in_position = False
                self.trades.append({"type": "sell_sl", "price": close_price})
                logging.info("SL HIT @ %.2f", close_price)
                action = {"action": "sell", "price": close_price}
        return action


class PaperEngineSimple:
    def __init__(self, starting_balance: float = 10000.0):
        self.balance = starting_balance
        self.position_qty = 0.0
        self.entry_price = 0.0
        self.history = []

    def buy(self, price: float, qty: float):
        cost = price * qty
        if cost > self.balance:
            logging.warning("Not enough balance to buy: needed %.2f have %.2f", cost, self.balance)
            return False
        self.balance -= cost
        self.position_qty = qty
        self.entry_price = price
        self.history.append({"side": "buy", "price": price, "qty": qty})
        logging.info("SIM BUY qty=%.6f @ %.2f | bal=%.2f", qty, price, self.balance)
        return True

    def sell(self, price: float):
        if self.position_qty <= 0:
            logging.warning("No position to sell")
            return False
        proceeds = price * self.position_qty
        self.balance += proceeds
        self.history.append({"side": "sell", "price": price, "qty": self.position_qty})
        logging.info("SIM SELL qty=%.6f @ %.2f | bal=%.2f", self.position_qty, price, self.balance)
        self.position_qty = 0.0
        return True


def run_sim():
    # synthetic price: gentle uptrend with noise
    prices = [100 + (i * 0.1) + ((-1) ** i) * 0.3 for i in range(400)]
    strat = SimpleStrategy(target_pct=0.05, stop_pct=0.02, risk_per_trade=0.01)
    engine = PaperEngineSimple(starting_balance=10000.0)

    for p in prices:
        action = strat.on_candle_close(p)
        if action["action"] == "buy":
            # naive sizing: buy so that risk_per_trade converts to qty given stop_pct
            stop_pct = strat.stop_pct
            risk = strat.risk_per_trade
            qty = (engine.balance * risk) / (p * stop_pct) if stop_pct > 0 else 0
            if qty > 0:
                engine.buy(p, qty)
        elif action["action"] == "sell":
            engine.sell(action["price"])
        time.sleep(0.005)

    logging.info("Simulation complete. Final balance: %.2f", engine.balance)
    logging.info("Trade history: %s", engine.history)


if __name__ == '__main__':
    run_sim()
