import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from dotenv import load_dotenv
import shioaji as sj
from datetime import datetime

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

api = None

def login():
    global api
    try:
        api = sj.Shioaji(simulation=False)
        accounts = api.login(
            api_key=os.environ["API_KEY"],
            secret_key=os.environ["SECRET_KEY"],
        )
        print(f"✅ 永豐金登入成功：{accounts[0].username}")

        api.activate_ca(
            ca_path=os.path.join(os.path.dirname(__file__), "../../", os.environ["CA_CERT_PATH"]),
            ca_passwd=os.environ["CA_PASSWORD"],
            person_id=os.environ.get("PERSON_ID", ""),
        )
        print("✅ 憑證啟動成功")
        return True
    except Exception as e:
        print(f"❌ 失敗：{e}")
        return False

def get_account_balance():
    if not api:
        return None
    try:
        balance = api.account_balance(api.stock_account)
        return {
            "available": float(balance.acc_balance),
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ 取得餘額失敗：{e}")
        return None

def get_positions():
    if not api:
        return []
    try:
        positions = api.list_positions(api.stock_account)
        result = []
        for p in positions:
            result.append({
                "symbol": p.code,
                "qty": p.quantity,
                "price": p.price,
                "pnl": p.pnl,
            })
        return result
    except Exception as e:
        print(f"❌ 取得持倉失敗：{e}")
        return []

def get_quote(symbol):
    if not api:
        return None
    try:
        contract = api.Contracts.Stocks[symbol]
        snapshot = api.snapshots([contract])
        if snapshot:
            s = snapshot[0]
            return {
                "symbol": symbol,
                "price": float(s.close),
                "change_pct": round((float(s.close) - float(s.open)) / float(s.open) * 100, 2) if s.open else 0,
                "volume": s.volume,
                "updated_at": datetime.now().isoformat()
            }
    except Exception as e:
        print(f"❌ 取得報價失敗：{e}")
        return None

def place_order(symbol, qty, action="Buy"):
    if not api:
        return None
    try:
        contract = api.Contracts.Stocks[symbol]
        order = api.Order(
            price=0,
            quantity=qty,
            action=sj.constant.Action.Buy if action=="Buy" else sj.constant.Action.Sell,
            price_type=sj.constant.StockPriceType.MKT,
            order_type=sj.constant.OrderType.ROD,
            account=api.stock_account
        )
        trade = api.place_order(contract, order)
        return {
            "order_id": trade.order.id,
            "symbol": symbol,
            "qty": qty,
            "action": action,
            "status": trade.status.status,
        }
    except Exception as e:
        print(f"❌ 下單失敗：{e}")
        return None

def logout():
    global api
    if api:
        api.logout()
        api = None
        print("✅ 已登出")

if __name__ == "__main__":
    print("=== 永豐金 API 連線測試 ===")
    if login():
        print("\n=== 帳戶餘額 ===")
        balance = get_account_balance()
        if balance:
            print(f"可用資金：${balance['available']:,.0f}")
        else:
            print("無法取得餘額")
        print("\n=== 目前持倉 ===")
        positions = get_positions()
        if positions:
            for p in positions:
                print(f"{p['symbol']}　數量：{p['qty']}　損益：${p['pnl']:,.0f}")
        else:
            print("目前無持倉")
        logout()
