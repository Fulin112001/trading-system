import requests
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from backend.trading_engine.strategy import SignalAggregator
from backend.config import get_risk_config
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_history(symbol, months=6):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={months}mo"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        candles = []
        for i in range(len(timestamps)):
            c = quotes["close"][i]
            o = quotes["open"][i]
            h = quotes["high"][i]
            l = quotes["low"][i]
            v = quotes["volume"][i]
            if all(x is not None for x in [c,o,h,l,v]):
                candles.append({
                    "date":   datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                    "open":   round(o,2),
                    "high":   round(h,2),
                    "low":    round(l,2),
                    "close":  round(c,2),
                    "volume": int(v),
                })
        return candles
    except Exception as e:
        print(f"資料取得失敗：{e}")
        return []

def run_backtest(symbol, initial_capital=10000, stop_loss_pct=3.0, take_profit_pct=6.0):
    print(f"\n📊 回測開始：{symbol}")
    candles = fetch_history(symbol, months=6)
    if len(candles) < 65:
        print(f"資料不足（{len(candles)} 筆），需要至少 65 筆")
        return None

    aggregator = SignalAggregator()
    capital     = initial_capital
    position    = None
    trades      = []
    equity_curve = [capital]

    for i in range(60, len(candles)):
        window   = [c["close"] for c in candles[:i+1]]
        current  = candles[i]
        price    = current["close"]

        # 檢查停損停利
        if position:
            pnl_pct = (price - position["entry"]) / position["entry"] * 100
            if position["direction"] == "BUY":
                if pnl_pct <= -stop_loss_pct or pnl_pct >= take_profit_pct:
                    pnl    = (price - position["entry"]) * position["qty"]
                    capital += pnl
                    trades.append({
                        "date":      current["date"],
                        "symbol":    symbol,
                        "direction": position["direction"],
                        "entry":     position["entry"],
                        "exit":      price,
                        "qty":       position["qty"],
                        "pnl":       round(pnl, 2),
                        "pnl_pct":   round(pnl_pct, 2),
                        "result":    "WIN" if pnl > 0 else "LOSS",
                    })
                    position = None

        # 產生訊號
        if not position:
            signal = aggregator.analyze(symbol, window, price)
            if signal.direction in ["BUY", "HOLD"] and signal.confidence >= 50:
                # 回測時只要不是明確 SELL 就嘗試進場
                pass
            # 單獨用均線判斷進場
            closes = window
            if len(closes) >= 20:
                ma5  = sum(closes[-5:]) / 5
                ma20 = sum(closes[-20:]) / 20
                prev_ma5  = sum(closes[-6:-1]) / 5
                prev_ma20 = sum(closes[-21:-1]) / 20
                if prev_ma5 < prev_ma20 and ma5 > ma20:
                    qty = round((capital * 0.1) / price, 4)
                    position = {"entry": price, "direction": "BUY", "qty": qty, "date": current["date"]}

        equity_curve.append(round(capital, 2))

    # 強制平倉最後持倉
    if position:
        price  = candles[-1]["close"]
        pnl    = (price - position["entry"]) * position["qty"]
        pnl_pct = (price - position["entry"]) / position["entry"] * 100
        capital += pnl
        trades.append({
            "date":      candles[-1]["date"],
            "symbol":    symbol,
            "direction": position["direction"],
            "entry":     position["entry"],
            "exit":      price,
            "qty":       position["qty"],
            "pnl":       round(pnl, 2),
            "pnl_pct":   round(pnl_pct, 2),
            "result":    "WIN" if pnl > 0 else "LOSS",
        })

    # 統計
    total_trades  = len(trades)
    wins          = [t for t in trades if t["result"] == "WIN"]
    losses        = [t for t in trades if t["result"] == "LOSS"]
    win_rate      = len(wins) / total_trades * 100 if total_trades else 0
    total_pnl     = sum(t["pnl"] for t in trades)
    avg_win       = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss      = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    profit_factor = abs(sum(t["pnl"] for t in wins) / sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else 0

    # 最大回撤
    peak     = initial_capital
    max_dd   = 0
    for eq in equity_curve:
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd: max_dd = dd

    result = {
        "symbol":          symbol,
        "period":          f"{candles[0]['date']} ~ {candles[-1]['date']}",
        "initial_capital": initial_capital,
        "final_capital":   round(capital, 2),
        "total_pnl":       round(total_pnl, 2),
        "total_return_pct":round((capital - initial_capital) / initial_capital * 100, 2),
        "total_trades":    total_trades,
        "win_rate":        round(win_rate, 1),
        "avg_win":         round(avg_win, 2),
        "avg_loss":        round(avg_loss, 2),
        "profit_factor":   round(profit_factor, 2),
        "max_drawdown":    round(max_dd, 2),
        "trades":          trades,
        "equity_curve":    equity_curve,
    }
    return result

def print_result(r):
    if not r: return
    print(f"\n{'='*45}")
    print(f"  {r['symbol']} 回測報告")
    print(f"  期間：{r['period']}")
    print(f"{'='*45}")
    print(f"  初始資金：  ${r['initial_capital']:>10,.2f}")
    print(f"  最終資金：  ${r['final_capital']:>10,.2f}")
    print(f"  總損益：    ${r['total_pnl']:>+10,.2f}  ({r['total_return_pct']:+.2f}%)")
    print(f"  最大回撤：  {r['max_drawdown']:.1f}%")
    print(f"{'─'*45}")
    print(f"  總交易次數：{r['total_trades']}")
    print(f"  勝率：      {r['win_rate']:.1f}%")
    print(f"  平均獲利：  ${r['avg_win']:>8,.2f}")
    print(f"  平均虧損：  ${r['avg_loss']:>8,.2f}")
    print(f"  Profit Factor：{r['profit_factor']:.2f}")
    print(f"{'─'*45}")
    print(f"  最近 5 筆交易：")
    for t in r['trades'][-5:]:
        icon = "✅" if t["result"] == "WIN" else "❌"
        print(f"  {icon} {t['date']}  {t['entry']:.2f}→{t['exit']:.2f}  {t['pnl_pct']:+.2f}%  ${t['pnl']:+.2f}")

if __name__ == "__main__":
    for symbol in ["BTC-USD", "0050.TW", "2330.TW"]:
        result = run_backtest(symbol, initial_capital=10000)
        print_result(result)
