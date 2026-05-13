import pandas as pd
import os
import sys
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from backend.database import init_db, Signal, Trade, RiskState, PersonalFinance, Watchlist
from backend.config import get_export_config

def export_to_excel():
    config = get_export_config()
    engine, Session = init_db()
    db = Session()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"trading_report_{timestamp}.xlsx"
    export_path = os.path.join(os.path.dirname(__file__), "..", config["export_path"])
    os.makedirs(export_path, exist_ok=True)
    filepath = os.path.join(export_path, filename)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        has_sheet = False

        # 訊號記錄
        signals = db.query(Signal).all()
        if signals:
            pd.DataFrame([{
                "時間": s.created_at, "標的": s.symbol,
                "方向": s.direction, "信心": s.confidence,
                "原因": s.reason, "策略": s.strategy,
                "市場狀態": s.market_state, "價格": s.price
            } for s in signals]).to_excel(writer, sheet_name="訊號記錄", index=False)
            has_sheet = True

        # 交易記錄
        trades = db.query(Trade).all()
        if trades:
            pd.DataFrame([{
                "時間": t.created_at, "標的": t.symbol,
                "方向": t.direction, "進場價": t.entry_price,
                "出場價": t.exit_price, "數量": t.quantity,
                "損益": t.pnl, "狀態": t.status, "券商": t.broker
            } for t in trades]).to_excel(writer, sheet_name="交易記錄", index=False)
            has_sheet = True

        # 個人財務
        finance = db.query(PersonalFinance).all()
        if finance:
            df = pd.DataFrame([{
                "時間": f.created_at, "類別": f.category,
                "細項": f.sub_category, "收支": f.type,
                "金額": f.amount, "創業項目": f.venture, "備註": f.note
            } for f in finance])
            df.to_excel(writer, sheet_name="個人財務", index=False)
            has_sheet = True

            ventures = df[df["創業項目"].notna() & (df["創業項目"] != "")]
            if not ventures.empty:
                summary = ventures.groupby(["創業項目", "收支"])["金額"].sum().unstack(fill_value=0)
                summary.to_excel(writer, sheet_name="創業項目小計")

        # 標的評估
        watchlist = db.query(Watchlist).all()
        if watchlist:
            pd.DataFrame([{
                "代號": w.symbol, "名稱": w.name,
                "市場": w.market, "總分": w.score,
                "基本面": w.fundamental_score,
                "技術面": w.technical_score,
                "狀態": w.status, "備註": w.note
            } for w in watchlist]).to_excel(writer, sheet_name="標的評估", index=False)
            has_sheet = True

        # 損益摘要
        if trades:
            closed = [t for t in trades if t.pnl is not None]
            total_pnl = sum(t.pnl for t in closed)
            wins = [t for t in closed if t.pnl > 0]
            win_rate = len(wins) / len(closed) * 100 if closed else 0
            losses = [t for t in closed if t.pnl < 0]
            pd.DataFrame([{
                "匯出時間": datetime.now(),
                "總交易次數": len(closed),
                "獲利次數": len(wins),
                "勝率": f"{win_rate:.1f}%",
                "總損益": total_pnl,
                "平均獲利": sum(t.pnl for t in wins) / len(wins) if wins else 0,
                "平均虧損": sum(t.pnl for t in losses) / len(losses) if losses else 0
            }], index=[0]).to_excel(writer, sheet_name="損益摘要", index=False)
            has_sheet = True

        # 沒有任何資料時建立空白摘要表
        if not has_sheet:
            pd.DataFrame([{
                "匯出時間": datetime.now(),
                "說明": "目前無交易資料"
            }]).to_excel(writer, sheet_name="摘要", index=False)

    db.close()
    print(f"✅ 匯出成功：{filepath}")

    if config.get("clear_after_export"):
        clear_db(engine, Session)

    return filepath

def clear_db(engine, Session):
    db = Session()
    db.query(Signal).delete()
    db.query(Trade).delete()
    db.query(RiskState).delete()
    db.commit()
    db.close()
    print("🗑️  資料庫已清空（個人財務與標的清單保留）")

if __name__ == "__main__":
    path = export_to_excel()
    print(f"檔案位置：{path}")

def export_and_notify():
    from discord.notifier import send_discord
    filepath = export_to_excel()
    filename = os.path.basename(filepath)
    
    # 取得資料庫摘要
    engine, Session = init_db()
    db = Session()
    trades = db.query(Trade).all()
    closed = [t for t in trades if t.pnl is not None]
    total_pnl = sum(t.pnl for t in closed) if closed else 0
    wins = [t for t in closed if t.pnl > 0]
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    signals_count = db.query(Signal).count()
    db.close()

    send_discord(
        f"**檔案：** `{filename}`\n"
        f"**訊號總數：** {signals_count}\n"
        f"**交易次數：** {len(closed)}\n"
        f"**勝率：** {win_rate:.1f}%\n"
        f"**總損益：** {'🟢 +' if total_pnl >= 0 else '🔴 '}${abs(total_pnl):,.2f}\n"
        f"**匯出時間：** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        title="📊 Excel 報表已產出",
        color=0x4f8ef7
    )
    return filepath

if __name__ == "__main__":
    export_and_notify()
