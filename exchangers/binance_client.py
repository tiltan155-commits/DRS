"""Binance client wrapper using python-binance.

Reads API keys from env by default. Supports testnet via `use_testnet` flag.
Provides simple helpers: get_price, get_balance, place_market_order (with dry_run support).
"""
import os
import logging
from typing import Optional, Dict, Any

try:
    from binance.client import Client
    from binance.enums import SIDE_BUY, SIDE_SELL
except Exception:
    Client = None


class BinanceClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, use_testnet: bool = True, dry_run: bool = True):
        if Client is None:
            logging.warning("python-binance not installed; BinanceClient will not work until you install requirements")
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.use_testnet = use_testnet if isinstance(use_testnet, bool) else (str(os.getenv("BINANCE_TESTNET", "true")).lower() == "true")
        self.dry_run = dry_run or (os.getenv("DRY_RUN", "true").lower() == "true")

        if Client:
            self.client = Client(self.api_key, self.api_secret)
            if self.use_testnet:
                # point to testnet REST endpoint
                try:
                    self.client.API_URL = "https://testnet.binance.vision/api"
                except Exception:
                    logging.debug("Could not set testnet API_URL")
        else:
            self.client = None

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """Return current price (ask/close) for symbol or None if unavailable."""
        if not self.client:
            logging.debug("Client not initialized")
            return None
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker.get("price"))
        except Exception:
            logging.exception("Error fetching price for %s", symbol)
            return None

    def get_balance(self, asset: str) -> Optional[float]:
        if not self.client:
            logging.debug("Client not initialized")
            return None
        try:
            info = self.client.get_asset_balance(asset=asset)
            if not info:
                return 0.0
            return float(info.get("free", 0.0))
        except Exception:
            logging.exception("Error fetching balance for %s", asset)
            return None

    def place_market_order(self, side: str, symbol: str, quantity: float) -> Dict[str, Any]:
        """Place a market order. If dry_run is True, do not send to exchange, just return simulated result."""
        side = side.upper()
        if self.dry_run or not self.client:
            logging.info("Dry-run: simulated %s market order %s qty=%.6f", side, symbol, quantity)
            return {"status": "SIMULATED", "side": side, "symbol": symbol, "executedQty": quantity}

        try:
            if side == "BUY":
                order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            else:
                order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
            logging.info("Order placed: %s", order)
            return order
        except Exception:
            logging.exception("Error placing market order: %s %s qty=%.6f", side, symbol, quantity)
            return {"status": "ERROR"}

    def get_account(self) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        try:
            return self.client.get_account()
        except Exception:
            logging.exception("Error getting account")
            return None
