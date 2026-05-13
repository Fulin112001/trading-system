# trading-system
Side project/ python learning/ trading self-education

# 🏦 Automated Trading System

A modular, fully self-hosted automated trading platform built from scratch. Designed around three decoupled engines — signal generation, risk management, and personal finance — with a real-time dashboard, Discord bot integration, and Docker deployment.

> Built as an independent project to explore quantitative trading system design, risk control architecture, and full-stack delivery.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Trading System                        │
├──────────────────┬──────────────────┬───────────────────┤
│  Trading Engine  │  Bankroll Engine │  Personal Finance │
│  Strategy Signal │  Risk & Position │  Capital Planning │
│  Generation      │  Management      │  & Venture P&L    │
└────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │   Signal Output  │  Risk Decision     │
         └──────────────────┤                    │
                            │                    │
                     Exchange API         Personal Data
                  (Sinopac / Bybit)        (SQLite)
```

**Key design principle:** The three modules are fully decoupled. Swapping brokers, strategies, or capital allocation never requires touching the other modules.

---

## Modules

### Trading Engine
- Multi-strategy signal generation: MA crossover, RSI, Bollinger Bands
- All strategy parameters configurable via JSON — no code changes required
- Confidence scoring and market state detection per signal
- Signal aggregator: requires N confirmations before triggering
- Backtesting module: win rate, Profit Factor, max drawdown, per-trade breakdown

### Bankroll Engine
- Three-tier risk mode: `NORMAL` → `DEFENSIVE` → `LOCKDOWN`
- Automatic mode switching based on consecutive losses, daily P&L, and total drawdown
- Position sizing with actual brokerage fee structure (TWD fractional shares)
- Emergency stop: one command halts all trading instantly
- Daily settlement with Discord report

### Personal Finance
- Separate from trading — tracks total personal capital
- Multi-venture P&L tracking (e.g. side business, freelance)
- Monthly income/expense summary
- Investment allocation health check

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python, FastAPI |
| Database | SQLite |
| Frontend | Vanilla JS, HTML/CSS |
| Market Data | Yahoo Finance REST API, CoinGecko API |
| Notifications | Discord Webhook |
| Deployment | Docker, Docker Compose |
| Broker Integration | Shioaji (Sinopac), Bybit API (configurable via JSON) |

---

## Features

- **Real-time market data** — Taiwan stocks, US ETFs, crypto (zero cost APIs)
- **Strategy backtesting** — run historical simulations with configurable parameters
- **Portfolio simulation** — paper trading with real fee calculations before going live
- **Watchlist scoring** — technical scoring system (MA trend, RSI, volume, 52-week position)
- **Discord Bot** — control the system from your phone
- **Auto scheduler** — morning market snapshot, daily settlement report, weekly Excel export
- **Multi-broker support** — switch between brokers by changing one line in JSON
- **Excel export** — auto-exports all data periodically, then clears the database to control storage costs

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Discord Webhook URL (for notifications)

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/trading-system.git
cd trading-system
```

Edit `config/settings.json`:

```json
{
  "capital": {
    "initial": 5000,
    "currency": "TWD"
  },
  "notification": {
    "discord_webhook": "YOUR_WEBHOOK_URL_HERE"
  },
  "active_broker": "sinopac"
}
```

Edit `config/portfolio.json` to set your portfolio allocations and watchlist.

### 2. Start the system

```bash
docker-compose up -d
```

That's it. The full system is now running:

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:80 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### 3. Stop the system

```bash
docker-compose down
```

---

## ⚠️ Important: Docker vs Local

**Do not run `python backend/api_server.py` while Docker is running.**
Both will bind to port 8000 and conflict with each other.

```bash
# ✅ Correct — use Docker
docker-compose up -d

# ❌ Wrong — do not run alongside Docker
python backend/api_server.py
```

---

## Discord Bot Commands

Send these commands in your Discord channel to control the system remotely from your phone:

| Command | Description |
|---------|-------------|
| `!help` | Show all commands |
| `!status` | Full system status |
| `!risk` | Risk mode and capital state |
| `!portfolio` | Current open positions |
| `!market` | Live market snapshot |
| `!stop` | 🔴 Emergency stop — halt all trading |
| `!pause` | Pause new trades, keep positions |
| `!resume` | Resume normal trading |
| `!report` | Generate and send Excel report to Discord |

---

## Configuration

All system behaviour is controlled via JSON — no code changes required for normal operation.

### `config/settings.json`

```json
{
  "active_broker": "sinopac",
  "capital": {
    "initial": 5000,
    "currency": "TWD"
  },
  "brokers": {
    "sinopac": { "api_key": "", "api_secret": "", "account": "" },
    "bybit":   { "api_key": "", "api_secret": "", "testnet": true }
  },
  "trading": {
    "strategies": {
      "ma_crossover": { "enabled": true, "fast_ma": 5, "slow_ma": 20, "long_ma": 60 },
      "rsi":          { "enabled": true, "period": 14, "overbought": 70, "oversold": 30 }
    },
    "signal": { "min_confirm": 2, "confidence_threshold": 60 }
  },
  "risk": {
    "daily_loss_limit_pct": 3.0,
    "max_drawdown_pct": 15.0,
    "max_consecutive_losses": 3,
    "position_size_pct": 20.0,
    "max_positions": 3
  },
  "notification": {
    "discord_webhook": "",
    "daily_report_time": "18:00"
  },
  "export": {
    "auto_export": true,
    "export_day": "sunday",
    "clear_after_export": true
  }
}
```

### Switching brokers

Change one line in `settings.json`:

```json
"active_broker": "bybit"
```

No other changes needed.

---

## Useful Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View backend logs
docker-compose logs -f trading-system

# View frontend logs
docker-compose logs -f trading-frontend

# Rebuild after code changes
docker-compose up -d --build

# Run a one-off command inside the container
docker exec trading-system python discord/bot.py '!status'
```

---

## Deploying to Raspberry Pi

This system is designed to run 24/7 on a Raspberry Pi (4, 2GB RAM minimum).

```bash
# On the Raspberry Pi
git clone https://github.com/yourusername/trading-system.git
cd trading-system

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Configure settings.json, then:
docker-compose up -d
```

Access the dashboard from any device on the same WiFi:
```
http://<raspberry-pi-ip>:80
```

---

## Project Status

| Module | Status |
|--------|--------|
| Trading Engine | ✅ Complete |
| Bankroll Engine | ✅ Complete |
| Personal Finance | ✅ Complete |
| Market Observer | ✅ Complete |
| Backtesting | ✅ Complete |
| Portfolio Simulation | ✅ Complete |
| Discord Bot | ✅ Complete |
| Docker Deployment | ✅ Complete |
| Sinopac (Shioaji) Live | 🔄 Pending account approval |
| Bybit Live | 🔄 Pending KYC |
| AI Strategy Module | 📋 Planned |

---

## Disclaimer

This system is for personal use and educational purposes. It is not financial advice. Always understand the risks before trading with real capital.

---

## Author

**Fulin Tseng** — fulin801028@gmail.com
