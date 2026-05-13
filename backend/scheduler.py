import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import time
import threading
from datetime import datetime, time as dtime
from backend.exporter import export_and_notify
from backend.market_observer import get_market_snapshot
from discord.notifier import notify_daily_report, send_discord
from backend.database import init_db, Trade, Signal
from backend.bankroll_engine.risk_manager import RiskManager

risk_manager = RiskManager(capital=10000)

def daily_settlement():
    engine, Session = init_db()
    db = Session()
    trades = db.query(Trade).all()
    closed = [t for t in trades if t.pnl is not None]
    total_pnl = sum(t.pnl for t in closed) if closed else 0
    wins = [t for t in closed if t.pnl > 0]
    win_rate = len(wins) / len(closed) * 100 if closed else 0
    db.close()
    notify_daily_report(
        capital=risk_manager.capital,
        daily_pnl=risk_manager.daily_pnl,
        win_rate=win_rate,
        risk_mode=risk_manager.mode,
        consecutive_losses=risk_manager.consecutive_losses
    )
    risk_manager.daily_reset()
    print(f"✅ 每日結算完成 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def weekly_export():
    print(f"📊 開始每週匯出...")
    export_and_notify()

def morning_snapshot():
    snapshot = get_market_snapshot()
    tw = snapshot.get("tw_stocks", {})
    crypto = snapshot.get("crypto", {})
    lines = ["**🌅 早安市場快照**\n"]
    if tw:
        lines.append("**🇹🇼 台股**")
        for sym, d in tw.items():
            arrow = "▲" if d["change_pct"] >= 0 else "▼"
            lines.append(f"{d['name']}　${d['price']:,.0f}　{arrow} {d['change_pct']:+.2f}%")
    if crypto:
        lines.append("\n**💰 加密貨幣**")
        for cid, d in crypto.items():
            arrow = "▲" if d["change_pct"] >= 0 else "▼"
            lines.append(f"{d['name']}　${d['price']:,.0f}　{arrow} {d['change_pct']:+.2f}%")
    send_discord("\n".join(lines), title="📊 早安快照", color=0x4f8ef7)
    print(f"✅ 早安快照發送完成 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def should_run(target_time, last_run):
    now = datetime.now().time()
    today = datetime.now().date()
    if last_run and last_run.date() == today:
        return False
    return now >= target_time

def run_scheduler():
    print("⏰ 排程啟動中...")
    last_morning  = None
    last_evening  = None
    last_weekly   = None

    MORNING_TIME  = dtime(8, 30)
    EVENING_TIME  = dtime(18, 0)
    WEEKLY_DAY    = 6  # 週日

    while True:
        now = datetime.now()

        # 早安快照 08:30
        if should_run(MORNING_TIME, last_morning):
            morning_snapshot()
            last_morning = now

        # 每日結算 18:00
        if should_run(EVENING_TIME, last_evening):
            daily_settlement()
            last_evening = now

        # 每週日匯出
        if now.weekday() == WEEKLY_DAY and should_run(dtime(20, 0), last_weekly):
            weekly_export()
            last_weekly = now

        time.sleep(60)  # 每分鐘檢查一次

def start_scheduler_thread():
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    print("⏰ 排程已在背景啟動")

if __name__ == "__main__":
    print("⏰ 排程測試模式")
    print("手動觸發早安快照...")
    morning_snapshot()
    print("手動觸發每日結算...")
    daily_settlement()
    print("✅ 測試完成")
