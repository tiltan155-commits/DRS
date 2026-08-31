"""WebSocket kline streamer (reused - supports testnet stream host)"""
import asyncio
import json
import logging
import ssl
import websockets


class BinanceWS:
    def __init__(self, symbol: str, interval: str = "1m", use_testnet: bool = True):
        self.symbol = symbol.lower()
        self.interval = interval
        self.base = "wss://testnet.binance.vision/ws" if use_testnet else "wss://stream.binance.com:9443/ws"
        self.url = f"{self.base}/{self.symbol}@kline_{self.interval}"

    async def _connect(self, on_message):
        logging.info(f"Connecting to ws {self.url}")
        ssl_context = ssl.create_default_context()
        async with websockets.connect(self.url, ssl=ssl_context) as ws:
            async for msg in ws:
                data = json.loads(msg)
                await on_message(data)

    def run(self, on_message):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._connect(on_message))
        except KeyboardInterrupt:
            logging.info("WebSocket stopped by user")
        except Exception:
            logging.exception("WebSocket error")
