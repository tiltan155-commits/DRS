# Binance Live feature (Testnet first)

This branch adds a live/trade-capable runner that connects the existing strategy to Binance (spot).

Files added:
- exchangers/binance_client.py  - wrapper around python-binance client with dry-run and testnet support
- order_manager.py             - safety checks, sizing and order placement logic
- binance_ws.py                - WebSocket kline streamer
- main_binance_live.py         - orchestrator to run strategy against Binance Testnet/Live
- config.yaml                  - parameters (symbol, TP/SL, risk, dry_run)
- .env.example                 - example env file for API keys
- requirements.txt             - dependencies

Safety notes:
- By default `dry_run: true` in config.yaml. Change to false only after you verify on testnet.
- Store API keys in environment variables (see .env.example). Never paste keys into chat.

How to run (Testnet recommended):
1. git checkout feature/binance-live
2. python3 -m venv venv && source venv/bin/activate
3. pip install -r requirements.txt
4. copy .env.example to .env and fill your testnet keys (or set env vars)
5. python main_binance_live.py

To go live:
- set BINANCE_TESTNET=false and dry_run=false (or cfg/dotenv change)
- ensure API key has trading permissions and you understand risks
