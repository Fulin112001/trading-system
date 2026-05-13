import json
import os
import sys
import requests
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime
from backend.database import init_db, Trade, PersonalFinance
from backend.trading_engine.strategy import SignalAggregator

HEADERS = {"User-Agent": "Mozilla/5.0"}
PORTFOLIO_PATH = os.path.join(os.path.dirname(__file__), "../config/portfolio.json")

def load_portfolio():
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_portfolio(data):
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        return round(closes[-1], 2) if closes else None
    except:
        return None

def calculate_fee(amount, portfolio_type):
    config = load_portfolio()["portfolios"][portfolio_type]
    fee = amount * config["fee_rate"]
    fee = max(fee, config["fee_min"])
    tax = amount * config["tax_rate"] if config["tax_rate"] else 0
    return round(fee + tax, 2)

def calculate_position_size(symbol, portfolio_type):
    config = load_portfolio()["portfolios"][portfolio_type]
    capital    = config["available_capital"]
    max_pct    = config["position"]["max_per_trade_pct"] / 100
    min_amount = config["position"]["min_trade_amount"]
    price      = get_price(symbol)
    if not price:
        return None, None, None
    amount     = capital * max_pct
    if amount < min_amount:
        return None, None, f"可用資金不足，最少需要 {min_amount}"
    fee        = calculate_fee(amount, portfolio_type)
    net_amount = amount - fee
    qty        = round(net_amount / price, 4)
    return qty, price, fee

def simulate_buy(symbol, portfolio_type, name=""):
    config     = load_portfolio()
    port       = config["portfolios"][portfolio_type]
    max_pos    = port["position"]["max_positions"]
    engine, Session = init_db()
    db         = Session()
    open_trades = db.query(Trade).filter(
        Trade.status == "open",
        Trade.broker == portfolio_type
    ).count()
    if open_trades >= max_pos:
        db.close()
        return None, f"已達最大持倉數 {max_pos}"
    existing = db.query(Trade).filter(
        Trade.symbol == symbol,
        Trade.status == "open",
        Trade.broker == portfolio_type
    ).first()
    if existing:
        db.close()
        return None, f"{symbol} 已有持倉"
    qty, price, fee = calculate_position_size(symbol, portfolio_type)
    if not qty:
        db.close()
        return None, fee
    amount = round(qty * price, 2)
    config["portfolios"][portfolio_type]["available_capital"] -= (amount + fee)
    save_portfolio(config)
    trade = Trade(
        symbol    = symbol,
        direction = "BUY",
        entry_price = price,
        quantity  = qty,
        status    = "open",
        broker    = portfolio_type,
        strategy  = "SIMULATION",
        stop_loss = round(price * (1 - port["strategies"]["exit"]["stop_loss_pct"] / 100), 2),
        take_profit = round(price * (1 + port["strategies"]["exit"]["take_profit_pct"] / 100), 2),
    )
    db.add(trade)
    db.commit()
    result = {
        "symbol":     symbol,
        "name":       name,
        "action":     "BUY",
        "price":      price,
        "qty":        qty,
        "amount":     amount,
        "fee":        fee,
        "stop_loss":  trade.stop_loss,
        "take_profit": trade.take_profit,
        "portfolio":  portfolio_type,
        "mode":       "模擬交易",
        "timestamp":  datetime.now().isoformat(),
    }
    db.close()
    return result, None

def simulate_sell(trade_id, portfolio_type):
    config   = load_portfolio()
    engine, Session = init_db()
    db       = Session()
    trade    = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        db.close()
        return None, "找不到交易"
    price    = get_price(trade.symbol)
    if not price:
        db.close()
        return None, "無法取得價格"
    fee      = calculate_fee(price * trade.quantity, portfolio_type)
    pnl      = round((price - trade.entry_price) * trade.quantity - fee, 2)
    pnl_pct  = round((price - trade.entry_price) / trade.entry_price * 100, 2)
    trade.exit_price = price
    trade.pnl        = pnl
    trade.status     = "closed"
    amount   = round(price * trade.quantity, 2)
    config["portfolios"][portfolio_type]["available_capital"] += (amount - fee)
    save_portfolio(config)
    db.commit()
    result = {
        "symbol":     trade.symbol,
        "action":     "SELL",
        "entry":      trade.entry_price,
        "exit":       price,
        "qty":        trade.quantity,
        "pnl":        pnl,
        "pnl_pct":    pnl_pct,
        "fee":        fee,
        "result":     "WIN" if pnl > 0 else "LOSS",
        "mode":       "模擬交易",
        "timestamp":  datetime.now().isoformat(),
    }
    db.close()
    return result, None

def get_portfolio_status(portfolio_type):
    config = load_portfolio()["portfolios"][portfolio_type]
    engine, Session = init_db()
    db     = Session()
    open_trades = db.query(Trade).filter(
        Trade.status == "open",
        Trade.broker == portfolio_type
    ).all()
    closed_trades = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.broker == portfolio_type
    ).all()
    positions = []
    unrealized_pnl = 0
    for t in open_trades:
        price = get_price(t.symbol)
        if price:
            upnl = round((price - t.entry_price) * t.quantity, 2)
            upnl_pct = round((price - t.entry_price) / t.entry_price * 100, 2)
            unrealized_pnl += upnl
            positions.append({
                "id":          t.id,
                "symbol":      t.symbol,
                "entry_price": t.entry_price,
                "current_price": price,
                "qty":         t.quantity,
                "unrealized_pnl": upnl,
                "unrealized_pnl_pct": upnl_pct,
                "stop_loss":   t.stop_loss,
                "take_profit": t.take_profit,
                "status":      "⚠️ 接近停損" if price <= t.stop_loss * 1.02 else "✅ 正常",
            })
    wins = [t for t in closed_trades if t.pnl and t.pnl > 0]
    realized_pnl = sum(t.pnl for t in closed_trades if t.pnl)
    win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0
    db.close()
    return {
        "name":             config["name"],
        "initial_capital":  config["initial_capital"],
        "available_capital": round(config["available_capital"], 2),
        "unrealized_pnl":   round(unrealized_pnl, 2),
        "realized_pnl":     round(realized_pnl, 2),
        "total_pnl":        round(unrealized_pnl + realized_pnl, 2),
        "open_positions":   len(open_trades),
        "closed_trades":    len(closed_trades),
        "win_rate":         round(win_rate, 1),
        "positions":        positions,
    }

def auto_check_positions(portfolio_type):
    config = load_portfolio()["portfolios"][portfolio_type]
    engine, Session = init_db()
    db     = Session()
    open_trades = db.query(Trade).filter(
        Trade.status == "open",
        Trade.broker == portfolio_type
    ).all()
    db.close()
    results = []
    for trade in open_trades:
        price = get_price(trade.symbol)
        if not price:
            continue
        sl  = trade.stop_loss
        tp  = trade.take_profit
        if price <= sl:
            result, err = simulate_sell(trade.id, portfolio_type)
            if result:
                results.append({**result, "trigger": "停損"})
        elif price >= tp:
            result, err = simulate_sell(trade.id, portfolio_type)
            if result:
                results.append({**result, "trigger": "停利"})
    return results

if __name__ == "__main__":
    print("=== 投資組合狀態 ===\n")
    for pt in ["tw_stock", "crypto"]:
        status = get_portfolio_status(pt)
        print(f"【{status['name']}】")
        print(f"  初始資金：  ${status['initial_capital']:,.0f}")
        print(f"  可用資金：  ${status['available_capital']:,.2f}")
        print(f"  未實現損益：${status['unrealized_pnl']:+,.2f}")
        print(f"  已實現損益：${status['realized_pnl']:+,.2f}")
        print(f"  持倉數：    {status['open_positions']}")
        print(f"  勝率：      {status['win_rate']:.1f}%\n")

    print("=== 模擬買入測試 ===")
    result, err = simulate_buy("0056.TW", "tw_stock", "元大高股息")
    if result:
        print(f"  ✅ 買入成功")
        print(f"  標的：{result['symbol']} {result['name']}")
        print(f"  價格：${result['price']}")
        print(f"  數量：{result['qty']} 股")
        print(f"  金額：${result['amount']}")
        print(f"  手續費：${result['fee']}")
        print(f"  停損：${result['stop_loss']}")
        print(f"  停利：${result['take_profit']}")
    else:
        print(f"  ❌ 買入失敗：{err}")
