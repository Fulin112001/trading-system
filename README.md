# 📈 Fulin Trading System

A modular, fully self-hosted automated trading platform built from scratch. Designed around three decoupled engines — signal generation, risk management, and personal finance — with real-time dashboard, Discord bot integration, and Docker deployment.

> Built as an independent project to explore quantitative trading system design, risk control architecture, and full-stack delivery.

🔗 **GitHub:** [github.com/Fulin112001/trading-system](https://github.com/Fulin112001/trading-system)

---

## 🗓️ Development Timeline

| Date | Milestone |
|------|-----------|
| 2026/05/13 | Project kickoff — architecture planning, module design |
| 2026/05/13 | Trading Engine: MA, RSI strategy modules + signal aggregator |
| 2026/05/13 | Bankroll Engine: risk modes, position sizing, emergency stop |
| 2026/05/13 | FastAPI backend + SQLite database |
| 2026/05/13 | Frontend Dashboard (5 pages) |
| 2026/05/13 | Discord Webhook notifications + auto scheduler |
| 2026/05/13 | Market observer: Yahoo Finance + CoinGecko APIs |
| 2026/05/13 | Watchlist scoring system + backtesting module |
| 2026/05/13 | Portfolio simulation with real fee structure |
| 2026/05/13 | Docker + Docker Compose deployment |
| 2026/05/13 | Trading journal module |
| 2026/05/14 | Sinopac Shioaji API — production environment connected |
| 2026/05/14 | Discord Bot — receive commands, auto-reply |
| 2026/05/14 | Personal finance password protection |

---

## Architecture

\`\`\`
┌─────────────────────────────────────────────────────────┐
│                    Fulin Trading System                  │
├──────────────────┬──────────────────┬───────────────────┤
│  Trading Engine  │  Bankroll Engine │  Personal Finance │
│  Strategy Signal │  Risk & Position │  Capital Planning │
│  Generation      │  Management      │  & Venture P&L    │
└────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │   Signal Output  │  Risk Decision     │
         └──────────────────┤                    │
                     Exchange API         Personal Data
                  (Sinopac / Bybit)        (SQLite)
\`\`\`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python, FastAPI |
| Database | SQLite |
| Frontend | Vanilla JS, HTML/CSS |
| Market Data | Yahoo Finance REST API, CoinGecko API |
| Broker | Sinopac Shioaji API (production) |
| Notifications | Discord Webhook + Discord Bot |
| Deployment | Docker, Docker Compose |

---

## Features

- Real-time market data — Taiwan stocks, US ETFs, crypto
- Multi-strategy signal generation (MA, RSI, Bollinger Bands)
- Three-tier risk management: NORMAL / DEFENSIVE / LOCKDOWN
- Backtesting with win rate, Profit Factor, max drawdown
- Portfolio simulation with real brokerage fee structure
- Trading journal — track observations and judgment accuracy
- Discord Bot — control system from phone
- Auto scheduler — morning snapshot, daily settlement, weekly export
- Multi-broker JSON config — switch brokers in one line
- Sinopac live API — real account, positions, order execution

---

## Quick Start

\`\`\`bash
git clone https://github.com/Fulin112001/trading-system.git
cd trading-system
# configure config/settings.json
docker-compose up -d
\`\`\`

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## ⚠️ Important

Do not run `python backend/api_server.py` while Docker is running — both bind to port 8000 and will conflict.

---

## Discord Bot Commands

| Command | Description |
|---------|-------------|
| `!help` | Show all commands |
| `!status` | System status |
| `!risk` | Risk mode and capital |
| `!portfolio` | Open positions |
| `!market` | Live market snapshot |
| `!stop` | 🔴 Emergency stop |
| `!pause` | Pause trading |
| `!resume` | Resume trading |
| `!report` | Generate Excel report |

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
| Trading Journal | ✅ Complete |
| Discord Bot | ✅ Complete |
| Docker Deployment | ✅ Complete |
| Sinopac Live API | ✅ Connected |
| Bybit Live | 🔄 Pending KYC |
| AI Strategy Module | 📋 Planned |

---

## Disclaimer

For personal use and educational purposes only. Not financial advice.

---

## Author

**Fulin Tseng** — fulin801028@gmail.com
[LinkedIn](https://linkedin.com/in/fulin-tseng-2bb6821b3) | [GitHub](https://github.com/Fulin112001)
