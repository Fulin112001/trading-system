import requests
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

TW_SYMBOLS = {
    "2330.TW": "台積電",
    "2454.TW": "聯發科",
    "2317.TW": "鴻海",
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
}

US_SYMBOLS = {
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq ETF",
}

CRYPTO_IDS = {
    "bitcoin":  "Bitcoin",
    "ethereum": "Ethereum",
    "solana":   "Solana",
}

def get_yahoo_quote(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None
        current = round(closes[-1], 2)
        prev    = round(closes[-2], 2)
        change     = round(current - prev, 2)
        change_pct = round((change / prev * 100) if prev else 0, 2)
        meta = result["meta"]
        return {
            "symbol":     symbol,
            "price":      current,
            "change":     change,
            "change_pct": change_pct,
            "currency":   meta.get("currency", ""),
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

def get_crypto_quotes():
    try:
        ids = ",".join(CRYPTO_IDS.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10)
        data = res.json()
        result = {}
        for coin_id, name in CRYPTO_IDS.items():
            if coin_id in data:
                price      = round(data[coin_id]["usd"], 2)
                change_pct = round(data[coin_id].get("usd_24h_change", 0), 2)
                result[coin_id] = {
                    "symbol":     coin_id,
                    "name":       name,
                    "price":      price,
                    "change_pct": change_pct,
                    "updated_at": datetime.now().isoformat(),
                }
        return result
    except Exception as e:
        return {}

def get_market_snapshot():
    snapshot = {
        "tw_stocks": {},
        "crypto":    {},
        "us_etf":    {},
        "timestamp": datetime.now().isoformat(),
    }
    for sym, name in TW_SYMBOLS.items():
        q = get_yahoo_quote(sym)
        if q and "error" not in q:
            snapshot["tw_stocks"][sym] = {**q, "name": name}
    for sym, name in US_SYMBOLS.items():
        q = get_yahoo_quote(sym)
        if q and "error" not in q:
            snapshot["us_etf"][sym] = {**q, "name": name}
    snapshot["crypto"] = get_crypto_quotes()
    return snapshot

def print_snapshot(snapshot):
    print("🇹🇼 台股")
    for sym, data in snapshot["tw_stocks"].items():
        arrow = "▲" if data["change_pct"] >= 0 else "▼"
        sign  = "+" if data["change_pct"] >= 0 else ""
        print(f"  {data['name']:8s}  ${data['price']:>10.2f}  {arrow} {sign}{data['change_pct']:.2f}%")

    print("\n💰 加密貨幣")
    for cid, data in snapshot["crypto"].items():
        arrow = "▲" if data["change_pct"] >= 0 else "▼"
        sign  = "+" if data["change_pct"] >= 0 else ""
        print(f"  {data['name']:10s}  ${data['price']:>10.2f}  {arrow} {sign}{data['change_pct']:.2f}%")

    print("\n🌍 美股 ETF")
    for sym, data in snapshot["us_etf"].items():
        arrow = "▲" if data["change_pct"] >= 0 else "▼"
        sign  = "+" if data["change_pct"] >= 0 else ""
        print(f"  {data['name']:12s}  ${data['price']:>10.2f}  {arrow} {sign}{data['change_pct']:.2f}%")

    print(f"\n⏰ 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    print("📡 取得市場快照中...\n")
    snapshot = get_market_snapshot()
    print_snapshot(snapshot)
