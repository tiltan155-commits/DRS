# Strategy module implementing EMA50 + RSI filter and TP/SL management

import time
import logging
from typing import List, Dict


def sma(prices: List[float], period: int) -> float:
    if len(prices) < period or period <= 0:
        return sum(prices) / len(prices) if prices else 0.0
    return sum(prices[-period:]) / period


def rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < 2:
        return 50.0
    gains = 0.0
    losses = 0.0
    # compute average gains/losses over last `period` intervals (simple non-smoothed)
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
        """
        Should be called on candle close. Returns dict with action: {"action": "buy"/"sell"/"hold", "price": float}
        """
        self.prices.append(close_price)
        sma50 = sma(self.prices, 50)
        current_rsi = rsi(self.prices, 14)
        action = {"action": "hold", "price": close_price}

        if not self.in_position:
            if close_price > sma50 and current_rsi > 50:
                self.in_position = True
                self.entry_price = close_price
                self.trades.append({"type": "buy", "price": close_price, "time": time.time()})
                logging.info("Strategy ENTER @ %.2f | RSI=%.1f SMA50=%.2f", close_price, current_rsi, sma50)
                action = {"action": "buy", "price": close_price}
            else:
                logging.debug("No entry: price=%.2f sma50=%.2f rsi=%.1f", close_price, sma50, current_rsi)
        else:
            # manage position
            if close_price >= self.entry_price * (1 + self.target_pct):
                self.in_position = False
                self.trades.append({"type": "sell_tp", "price": close_price, "time": time.time()})
                logging.info("Strategy TP @ %.2f", close_price)
                action = {"action": "sell", "price": close_price}
            elif close_price <= self.entry_price * (1 - self.stop_pct):
                self.in_position = False
                self.trades.append({"type": "sell_sl", "price": close_price, "time": time.time()})
                logging.info("Strategy SL @ %.2f", close_price)
                action = {"action": "sell", "price": close_price}
            else:
                logging.debug("Holding position. price=%.2f", close_price)

        return action
