# AI-TRADING MVP

A modular Python 3.11 MVP for automated US equities paper trading on **30-minute bars** using **Alpaca**.

## Architecture

Execution flow:

`scheduler -> fetch market data -> strategy signal -> risk check -> order execution -> portfolio update -> logging`

Project modules:

- `config/`: environment-driven settings
- `data/`: market data ingestion and PostgreSQL storage
- `strategy/`: indicators and moving average crossover signal engine
- `risk/`: position sizing, duplicate-order, and drawdown checks
- `execution/`: signal-to-order conversion
- `broker/`: Alpaca abstraction layer
- `portfolio/`: account/positions snapshots and daily PnL
- `scheduler/`: 30-minute APScheduler job orchestration
- `logs/`: runtime logs

## Prerequisites

- Python 3.11
- Docker + Docker Compose
- Alpaca paper account credentials

## Setup

1. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start PostgreSQL:

```bash
docker compose up -d postgres
```

3. Create `.env` in the project root:

```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_FEED=iex
TRADE_SYMBOLS=AAPL,MSFT
BAR_TIMEFRAME=30Min
FAST_MA_WINDOW=5
SLOW_MA_WINDOW=20
MAX_POSITION_PCT=0.10
MAX_DAILY_DRAWDOWN_PCT=0.05
POSTGRES_URL=postgresql+psycopg2://trader:trader@localhost:5432/trading
SCHEDULER_TIMEZONE=America/New_York
```

4. Run the bot:

```bash
python main.py
```

The app initializes tables, executes one immediate cycle, and then runs every 30 minutes.

## Notes

- This MVP is configured for **paper trading** only.
- To switch to live trading later, replace/extend the broker adapter in `broker/alpaca_broker.py`.
- Logs are written to `logs/trading.log` and key entities are persisted in PostgreSQL.
