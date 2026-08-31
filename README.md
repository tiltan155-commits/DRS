# Binance paper trading feature

This branch implements a simple paper-trading connection to Binance (testnet) and a basic EMA50+RSI strategy.

Files added:
- binance_ws.py - minimal websocket streamer
- paper_engine.py - naive paper exchange simulator
- strategy.py - strategy implementation (EMA50+RSI, TP/SL)
- main_binance_paper.py - orchestrator to run the paper strategy against Binance kline stream
- config.yaml - parameters
- requirements.txt

How to run (local):
1. python3 -m venv venv
2. source venv/bin/activate
3. pip install -r requirements.txt
4. python main_binance_paper.py

Notes:
- This is intended for paper/testing. Do NOT put real API keys in config.yaml. For live trading, additional safety checks and order handling are required.
