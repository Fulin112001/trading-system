import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from backend.config import load_config, switch_broker, get_risk_config
from backend.database import init_db, Signal, Trade, RiskState, PersonalFinance, Watchlist
from backend.bankroll_engine.risk_manager import RiskManager
from backend.trading_engine.strategy import SignalAggregator
import random

app = FastAPI(title="Trading System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine, Session = init_db()
def get_risk_manager():
    config = load_config()
    capital = config.get("capital", {}).get("initial", 10000)
    return RiskManager(capital=capital)

risk_manager = get_risk_manager()

class TradeRequest(BaseModel):
    symbol: str
    direction: str
    price: float
    quantity: float

class FinanceEntry(BaseModel):
    category: str
    sub_category: str
    type: str
    amount: float
    note: str = ""
    venture: str = ""

class WatchlistEntry(BaseModel):
    symbol: str
    name: str
    market: str
    note: str = ""

class BrokerSwitch(BaseModel):
    broker: str

# ── 系統狀態 ──
@app.get("/api/status")
def get_status():
    config = load_config()
    return {
        "active_broker": config["active_broker"],
        "broker_name": config["brokers"][config["active_broker"]]["name"],
        "market": config["brokers"][config["active_broker"]]["market"],
        "risk": risk_manager.get_status(),
        "timestamp": datetime.now().isoformat()
    }

# ── Trading Engine ──
@app.get("/api/signals")
def get_signals():
    db = Session()
    signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(20).all()
    db.close()
    return [{"id": s.id, "symbol": s.symbol, "direction": s.direction,
             "confidence": s.confidence, "reason": s.reason,
             "strategy": s.strategy, "price": s.price,
             "created_at": s.created_at.isoformat()} for s in signals]

@app.get("/api/signals/analyze/{symbol}")
def analyze_symbol(symbol: str):
    prices = [100 + random.uniform(-5, 5) for _ in range(80)]
    current_price = prices[-1]
    aggregator = SignalAggregator()
    signal = aggregator.analyze(symbol, prices, current_price)
    result = signal.to_dict()

    db = Session()
    db_signal = Signal(
        symbol=signal.symbol, direction=signal.direction,
        confidence=signal.confidence, reason=signal.reason,
        strategy=signal.strategy, price=signal.price,
        market_state=signal.market_state
    )
    db.add(db_signal)
    db.commit()
    db.close()
    return result

# ── Bankroll Engine ──
@app.get("/api/risk/status")
def get_risk_status():
    return risk_manager.get_status()

@app.post("/api/risk/emergency-stop")
def emergency_stop():
    risk_manager.emergency_stop_all()
    return {"status": "emergency_stop_activated", "timestamp": datetime.now().isoformat()}

@app.post("/api/risk/resume")
def resume_trading():
    risk_manager.resume_trading()
    return {"status": "resumed", "mode": risk_manager.mode}

@app.post("/api/risk/pause")
def pause_trading():
    risk_manager.emergency_stop = True
    return {"status": "paused", "message": "暫停交易，保留倉位"}

@app.get("/api/trades")
def get_trades():
    db = Session()
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(50).all()
    db.close()
    return [{"id": t.id, "symbol": t.symbol, "direction": t.direction,
             "entry_price": t.entry_price, "exit_price": t.exit_price,
             "quantity": t.quantity, "pnl": t.pnl, "status": t.status,
             "created_at": t.created_at.isoformat()} for t in trades]

# ── 個人財務 ──
@app.get("/api/finance")
def get_finance():
    db = Session()
    entries = db.query(PersonalFinance).order_by(PersonalFinance.created_at.desc()).limit(100).all()
    db.close()
    return [{"id": e.id, "category": e.category, "sub_category": e.sub_category,
             "type": e.type, "amount": e.amount, "note": e.note,
             "venture": e.venture, "created_at": e.created_at.isoformat()} for e in entries]

@app.post("/api/finance")
def add_finance(entry: FinanceEntry):
    db = Session()
    record = PersonalFinance(
        category=entry.category, sub_category=entry.sub_category,
        type=entry.type, amount=entry.amount,
        note=entry.note, venture=entry.venture
    )
    db.add(record)
    db.commit()
    db.close()
    return {"status": "success", "message": "記錄新增成功"}

@app.get("/api/finance/summary")
def get_finance_summary():
    db = Session()
    entries = db.query(PersonalFinance).all()
    db.close()
    total_income = sum(e.amount for e in entries if e.type == "income")
    total_expense = sum(e.amount for e in entries if e.type == "expense")
    ventures = {}
    for e in entries:
        if e.venture:
            if e.venture not in ventures:
                ventures[e.venture] = {"income": 0, "expense": 0}
            if e.type == "income":
                ventures[e.venture]["income"] += e.amount
            else:
                ventures[e.venture]["expense"] += e.amount
    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "net": round(total_income - total_expense, 2),
        "ventures": ventures
    }

# ── 標的評估 ──
@app.get("/api/watchlist")
def get_watchlist():
    db = Session()
    items = db.query(Watchlist).order_by(Watchlist.score.desc()).all()
    db.close()
    return [{"id": w.id, "symbol": w.symbol, "name": w.name,
             "market": w.market, "score": w.score,
             "fundamental_score": w.fundamental_score,
             "technical_score": w.technical_score,
             "status": w.status, "note": w.note} for w in items]

@app.post("/api/watchlist")
def add_watchlist(entry: WatchlistEntry):
    db = Session()
    item = Watchlist(
        symbol=entry.symbol, name=entry.name,
        market=entry.market, note=entry.note
    )
    db.add(item)
    db.commit()
    db.close()
    return {"status": "success", "message": f"{entry.symbol} 已加入追蹤清單"}

# ── 券商切換 ──
@app.post("/api/broker/switch")
def switch_broker_api(req: BrokerSwitch):
    success = switch_broker(req.broker)
    if not success:
        raise HTTPException(status_code=400, detail="找不到指定券商")
    return {"status": "success", "active_broker": req.broker}

from backend.market_observer import get_market_snapshot, get_yahoo_quote, get_crypto_quotes

@app.get("/api/market/snapshot")
def market_snapshot():
    return get_market_snapshot()

@app.get("/api/market/quote/{symbol}")
def market_quote(symbol: str):
    return get_yahoo_quote(symbol)

@app.get("/api/market/crypto")
def market_crypto():
    return get_crypto_quotes()



@app.delete("/api/watchlist/{item_id}")
def delete_watchlist(item_id: int):
    db = Session()
    item = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="找不到標的")
    db.delete(item)
    db.commit()
    db.close()
    return {"status": "success", "message": "已刪除"}

from backend.stock_evaluator import evaluate_and_save, evaluate_symbol

@app.get("/api/evaluate/{symbol}")
def evaluate(symbol: str, name: str = "", market: str = "TW_STOCK"):
    result = evaluate_and_save(symbol, name, market)
    if not result:
        raise HTTPException(status_code=404, detail="無法取得資料")
    return result

@app.post("/api/evaluate/batch")
def evaluate_batch(symbols: list[dict]):
    results = []
    for item in symbols:
        result = evaluate_and_save(
            item.get("symbol",""),
            item.get("name",""),
            item.get("market","TW_STOCK")
        )
        if result:
            results.append(result)
    return results

from backend.scheduler import start_scheduler_thread
start_scheduler_thread()


from backend.portfolio_engine import (
    get_portfolio_status, simulate_buy, simulate_sell,
    auto_check_positions, load_portfolio
)
from backend.backtest import run_backtest

class BuyRequest(BaseModel):
    symbol: str
    name: str = ""
    portfolio_type: str = "tw_stock"

class SellRequest(BaseModel):
    trade_id: int
    portfolio_type: str = "tw_stock"

class BacktestRequest(BaseModel):
    symbol: str
    initial_capital: float = 10000
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0

@app.get("/api/portfolio/{portfolio_type}")
def portfolio_status(portfolio_type: str):
    return get_portfolio_status(portfolio_type)

@app.get("/api/portfolio")
def all_portfolios():
    return {
        "tw_stock": get_portfolio_status("tw_stock"),
        "crypto":   get_portfolio_status("crypto"),
    }

@app.post("/api/portfolio/buy")
def portfolio_buy(req: BuyRequest):
    result, err = simulate_buy(req.symbol, req.portfolio_type, req.name)
    if err: raise HTTPException(status_code=400, detail=err)
    return result

@app.post("/api/portfolio/sell")
def portfolio_sell(req: SellRequest):
    result, err = simulate_sell(req.trade_id, req.portfolio_type)
    if err: raise HTTPException(status_code=400, detail=err)
    return result

@app.post("/api/portfolio/check")
def check_positions(portfolio_type: str = "tw_stock"):
    return auto_check_positions(portfolio_type)

@app.post("/api/backtest")
def backtest(req: BacktestRequest):
    result = run_backtest(req.symbol, req.initial_capital, req.stop_loss_pct, req.take_profit_pct)
    if not result: raise HTTPException(status_code=400, detail="回測失敗，資料不足")
    return result


import hashlib

class LoginRequest(BaseModel):
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    config = load_config()
    correct = config.get("finance_password", "")
    hashed = hashlib.sha256(req.password.encode()).hexdigest()
    if hashed == correct:
        return {"status": "success", "token": hashed}
    raise HTTPException(status_code=401, detail="密碼錯誤")


import hashlib

class LoginRequest(BaseModel):
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    config = load_config()
    correct = config.get("finance_password", "")
    hashed = hashlib.sha256(req.password.encode()).hexdigest()
    if hashed == correct:
        return {"status": "success", "token": hashed}
    raise HTTPException(status_code=401, detail="密碼錯誤")


from backend.broker.sinopac import login as sinopac_login, get_account_balance, get_positions, get_quote as sinopac_quote, logout as sinopac_logout

sinopac_connected = False

@app.post("/api/sinopac/connect")
def sinopac_connect():
    global sinopac_connected
    result = sinopac_login()
    sinopac_connected = result
    return {"status": "success" if result else "failed", "connected": sinopac_connected}

@app.get("/api/sinopac/balance")
def sinopac_balance():
    if not sinopac_connected:
        raise HTTPException(status_code=400, detail="請先連線永豐金")
    balance = get_account_balance()
    if not balance:
        raise HTTPException(status_code=400, detail="無法取得餘額")
    return balance

@app.get("/api/sinopac/positions")
def sinopac_positions():
    if not sinopac_connected:
        raise HTTPException(status_code=400, detail="請先連線永豐金")
    return get_positions()

@app.get("/api/sinopac/quote/{symbol}")
def sinopac_get_quote(symbol: str):
    if not sinopac_connected:
        raise HTTPException(status_code=400, detail="請先連線永豐金")
    result = sinopac_quote(symbol)
    if not result:
        raise HTTPException(status_code=400, detail="無法取得報價")
    return result

@app.post("/api/sinopac/disconnect")
def sinopac_disconnect():
    global sinopac_connected
    sinopac_logout()
    sinopac_connected = False
    return {"status": "disconnected"}


import threading

def start_discord_bot():
    try:
        import sys
        sys.path.append(os.path.dirname(__file__) + "/..")
        from discord.discord_bot import run_bot
        run_bot()
    except Exception as e:
        print(f"❌ Discord Bot 啟動失敗：{e}")

discord_bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
discord_bot_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
