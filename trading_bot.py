#!/usr/bin/env python3
import time
import logging
from typing import Tuple, List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --- Simple indicator implementations (can be replaced with 'ta' library) ---

def sma(prices: list, period: int) -> float:
    if len(prices) < period or period <= 0:
        return sum(prices) / len(prices) if prices else 0.0
    return sum(prices[-period:]) / period


def ema(prices: list, period: int, prev_ema: float = None) -> float:
    if not prices:
        return 0.0
    k = 2 / (period + 1)
    if prev_ema is None:
        return sma(prices, period)
    return prices[-1] * k + prev_ema * (1 - k)


def rsi(prices: list, period: int = 14) -> float:
    if len(prices) < 2:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(1, min(len(prices), period + 1)):
        change = prices[-i] - prices[-i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    if gains + losses == 0:
        return 50.0
    rs = (gains / period) / (losses / period) if losses != 0 else float('inf')
    return 100 - (100 / (1 + rs))


# --- Market data / paper exchange simulator ---

class PaperMarket:
    """Very small paper-market simulator using a price series."""
    def __init__(self, price_series: list):
        self.prices = price_series
        self.index = 0

    def get_latest_price(self) -> float:
        if self.index >= len(self.prices):
            return self.prices[-1]
        p = self.prices[self.index]
        self.index += 1
        return p


# --- Strategy implementation (default: EMA50 + RSI filter, TP 5%, SL 2%) ---

class SimpleStrategy:
    def __init__(
        self,
        target_pct: float = 0.05,
        stop_pct: float = 0.02,
        risk_per_trade: float = 0.01,
        timeframe: str = "1m",
    ):
        self.target_pct = target_pct
        self.stop_pct = stop_pct
        self.risk_per_trade = risk_per_trade
        self.timeframe = timeframe
        self.prices: list = []
        self.in_position = False
        self.buy_price = 0.0
        self.trades: List[Dict] = []

    def on_price(self, price: float):
        self.prices.append(price)

        # Compute simple indicators
        sma50 = sma(self.prices, 50)
        current_rsi = rsi(self.prices, 14)

        # Trend condition: price > SMA50 and RSI > 50
        trend = price > sma50 and current_rsi > 50

        if not self.in_position:
            if trend:
                # Enter market (paper) at market price
                self.buy_price = price
                self.in_position = True
                entry = {"type": "buy", "price": price, "rsi": current_rsi, "sma50": sma50, "time": time.time()}
                self.trades.append(entry)
                logging.info(f"ENTER @ {price:.2f} | RSI={current_rsi:.1f} | SMA50={sma50:.2f}")
            else:
                logging.debug(f"No entry. price={price:.2f} sma50={sma50:.2f} rsi={current_rsi:.1f}")
        else:
            # Manage open position
            if price >= self.buy_price * (1 + self.target_pct):
                self.in_position = False
                self.trades.append({"type": "sell_tp", "price": price, "time": time.time()})
                logging.info(f"TP HIT @ {price:.2f} (+{self.target_pct*100:.1f}%)")
            elif price <= self.buy_price * (1 - self.stop_pct):
                self.in_position = False
                self.trades.append({"type": "sell_sl", "price": price, "time": time.time()})
                logging.info(f"SL HIT @ {price:.2f} (-{self.stop_pct*100:.1f}%)")
            else:
                logging.debug(f"Holding. price={price:.2f}")


# --- Runner / simple test harness ---

def run_paper_bot(price_series: list, max_steps: int = 0):
    market = PaperMarket(price_series)
    strat = SimpleStrategy(target_pct=0.05, stop_pct=0.02, risk_per_trade=0.01)

    steps = 0
    try:
        while True:
            price = market.get_latest_price()
            strat.on_price(price)
            steps += 1
            if max_steps and steps >= max_steps:
                break
            time.sleep(0.01)  # fast simulation delay
    except KeyboardInterrupt:
        logging.info("Interrupted")
    finally:
        logging.info("Trades summary:")
        for t in strat.trades:
            logging.info(t)


# --- Example usage ---
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    # Example synthetic price series: small uptrend with noise
    prices = [100 + (i * 0.1) + ((-1) ** i) * 0.2 for i in range(200)]

    run_paper_bot(prices, max_steps=200)
