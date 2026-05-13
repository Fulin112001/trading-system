import requests
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from backend.market_observer import get_yahoo_quote
from backend.database import init_db, Watchlist
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_fundamentals(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        volumes = result["indicators"]["quote"][0]["volume"]
        volumes = [v for v in volumes if v is not None]
        high_52w = max(closes[-min(60,len(closes)):]) if closes else None
        low_52w  = min(closes[-min(60,len(closes)):]) if closes else None
        avg_vol  = sum(volumes) / len(volumes) if volumes else None
        return {
            "currency":   meta.get("currency"),
            "high_52w":   round(high_52w, 2) if high_52w else None,
            "low_52w":    round(low_52w, 2) if low_52w else None,
            "avg_volume": int(avg_vol) if avg_vol else None,
            "current":    round(closes[-1], 2) if closes else None,
        }
    except:
        return {}

def score_technical(symbol):
    scores = {}
    details = {}
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=6mo"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        volumes = result["indicators"]["quote"][0]["volume"]
        volumes = [v for v in volumes if v is not None]

        if len(closes) < 20:
            return 50, {"error": "資料不足"}

        current = closes[-1]

        # 1. 均線趨勢（25分）
        ma5  = sum(closes[-5:])  / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-min(60,len(closes)):]) / min(60,len(closes))
        ma_score = 0
        if current > ma5:  ma_score += 5
        if current > ma20: ma_score += 5
        if current > ma60: ma_score += 5
        if ma5 > ma20:     ma_score += 5
        if ma20 > ma60:    ma_score += 5
        scores["均線趨勢"] = ma_score
        details["均線"] = f"MA5={ma5:.1f} MA20={ma20:.1f} MA60={ma60:.1f}"

        # 2. RSI（25分）
        period = 14
        gains, losses = [], []
        for i in range(1, min(period+1, len(closes))):
            diff = closes[-i] - closes[-i-1]
            if diff > 0: gains.append(diff)
            else: losses.append(abs(diff))
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0.001
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        if 45 <= rsi <= 65:   rsi_score = 25
        elif 35 <= rsi < 45:  rsi_score = 20
        elif 65 < rsi <= 75:  rsi_score = 15
        elif 25 <= rsi < 35:  rsi_score = 10
        else:                 rsi_score = 5
        scores["RSI"] = rsi_score
        details["RSI"] = f"{rsi:.1f}"

        # 3. 成交量趨勢（25分）
        avg_vol_recent = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
        avg_vol_old    = sum(volumes[-20:-5]) / 15 if len(volumes) >= 20 else avg_vol_recent
        if avg_vol_recent > avg_vol_old * 1.5:   vol_score = 25
        elif avg_vol_recent > avg_vol_old * 1.2: vol_score = 20
        elif avg_vol_recent > avg_vol_old:        vol_score = 15
        elif avg_vol_recent > avg_vol_old * 0.8: vol_score = 10
        else:                                     vol_score = 5
        scores["成交量"] = vol_score
        details["成交量"] = f"近5日均量 {int(avg_vol_recent):,}"

        # 4. 年內位置（25分）
        high_52w = max(closes[-min(120,len(closes)):])
        low_52w  = min(closes[-min(120,len(closes)):])
        position = (current - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50
        if 30 <= position <= 70:   pos_score = 25
        elif 20 <= position < 30:  pos_score = 20
        elif 70 < position <= 80:  pos_score = 15
        elif 10 <= position < 20:  pos_score = 10
        else:                      pos_score = 5
        scores["年內位置"] = pos_score
        details["年內位置"] = f"{position:.1f}% (最高${high_52w:.1f} 最低${low_52w:.1f})"

        total = sum(scores.values())
        return total, {**scores, "detail": details}

    except Exception as e:
        return 50, {"error": str(e)}

def evaluate_symbol(symbol, name="", market="TW_STOCK"):
    print(f"  評估 {symbol}...")
    quote = get_yahoo_quote(symbol)
    if not quote or "error" in quote:
        return None

    tech_score, tech_detail = score_technical(symbol)
    fundamentals = get_fundamentals(symbol)

    # 最終評分（技術面為主，基本面輔助）
    final_score = round(tech_score, 1)

    # 建議
    if final_score >= 80:   recommendation = "強力推薦"
    elif final_score >= 65: recommendation = "值得關注"
    elif final_score >= 50: recommendation = "中性觀望"
    else:                   recommendation = "暫時迴避"

    return {
        "symbol":         symbol,
        "name":           name or symbol,
        "market":         market,
        "price":          quote["price"],
        "change_pct":     quote["change_pct"],
        "technical_score": tech_score,
        "final_score":    final_score,
        "recommendation": recommendation,
        "detail":         tech_detail,
        "fundamentals":   fundamentals,
        "evaluated_at":   datetime.now().isoformat(),
    }

def evaluate_and_save(symbol, name="", market="TW_STOCK"):
    result = evaluate_symbol(symbol, name, market)
    if not result:
        return None
    engine, Session = init_db()
    db = Session()
    existing = db.query(Watchlist).filter(Watchlist.symbol == symbol).first()
    if existing:
        existing.score = result["final_score"]
        existing.technical_score = result["technical_score"]
        existing.name = name or symbol
    else:
        item = Watchlist(
            symbol=symbol, name=name or symbol,
            market=market,
            score=result["final_score"],
            technical_score=result["technical_score"],
        )
        db.add(item)
    db.commit()
    db.close()
    return result

if __name__ == "__main__":
    targets = [
        ("2330.TW", "台積電",    "TW_STOCK"),
        ("0050.TW", "元大台灣50", "TW_STOCK"),
        ("BTC-USD", "Bitcoin",   "CRYPTO"),
    ]
    print("📊 標的評估開始...\n")
    for symbol, name, market in targets:
        result = evaluate_and_save(symbol, name, market)
        if result:
            print(f"\n{'='*40}")
            print(f"  {result['name']} ({result['symbol']})")
            print(f"  現價：${result['price']:,.2f}  漲跌：{result['change_pct']:+.2f}%")
            print(f"  技術面評分：{result['technical_score']}/100")
            print(f"  綜合評分：  {result['final_score']}/100")
            print(f"  建議：      {result['recommendation']}")
            print(f"  評分細項：")
            for k, v in result['detail'].items():
                if k != 'detail':
                    print(f"    {k}: {v}")
    print("\n✅ 評估完成，已儲存至資料庫")
