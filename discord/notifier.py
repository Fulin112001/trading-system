import requests
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from backend.config import get_notification_config
from datetime import datetime

def send_discord(message: str, title: str = None, color: int = None):
    config = get_notification_config()
    webhook = config.get("discord_webhook", "")
    if not webhook:
        print("⚠️  Discord Webhook 尚未設定")
        return False
    payload = {"embeds": [{"description": message, "timestamp": datetime.utcnow().isoformat()}]}
    if title: payload["embeds"][0]["title"] = title
    if color: payload["embeds"][0]["color"] = color
    res = requests.post(webhook, json=payload)
    return res.status_code == 204

def notify_signal(symbol, direction, confidence, reason):
    if not get_notification_config().get("notify_on_signal"): return
    colors = {"BUY": 0x00ff88, "SELL": 0xff1a4b, "HOLD": 0x7a6d8a}
    icons  = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}
    send_discord(
        f"**標的：** {symbol}\n**信心：** {confidence:.1f}%\n**原因：** {reason}",
        title=f"{icons.get(direction,'')} {direction} 訊號 — {symbol}",
        color=colors.get(direction, 0x7a6d8a)
    )

def notify_trade(symbol, direction, price, quantity, pnl=None):
    if not get_notification_config().get("notify_on_trade"): return
    msg = f"**標的：** {symbol}\n**方向：** {direction}\n**價格：** ${price}\n**數量：** {quantity}"
    if pnl is not None:
        msg += f"\n**損益：** {'🟢 +' if pnl >= 0 else '🔴 '}${abs(pnl):.2f}"
    send_discord(msg, title=f"📊 交易執行 — {symbol}", color=0x4f8ef7)

def notify_risk_mode(old_mode, new_mode):
    if not get_notification_config().get("notify_on_risk_mode_change"): return
    colors = {"NORMAL": 0x00ff88, "DEFENSIVE": 0xffe033, "LOCKDOWN": 0xff1a4b}
    icons  = {"NORMAL": "✅", "DEFENSIVE": "⚠️", "LOCKDOWN": "🔴"}
    send_discord(
        f"風控模式從 **{old_mode}** 切換為 **{new_mode}**\n時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title=f"{icons.get(new_mode,'')} 風控模式變更",
        color=colors.get(new_mode, 0x7a6d8a)
    )

def notify_daily_report(capital, daily_pnl, win_rate, risk_mode, consecutive_losses):
    pnl_icon = "🟢" if daily_pnl >= 0 else "🔴"
    send_discord(
        f"**資金：** ${capital:,.2f}\n"
        f"**今日損益：** {pnl_icon} {'+'if daily_pnl>=0 else ''}${daily_pnl:,.2f}\n"
        f"**勝率：** {win_rate:.1f}%\n"
        f"**風控模式：** {risk_mode}\n"
        f"**連敗次數：** {consecutive_losses}",
        title=f"📋 每日報告 — {datetime.now().strftime('%Y/%m/%d')}",
        color=0x4f8ef7
    )

def notify_emergency(action):
    send_discord(
        f"**動作：** {action}\n**時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="🚨 緊急操作",
        color=0xff1a4b
    )

if __name__ == "__main__":
    print("測試 Discord 通知...")
    notify_signal("2330", "BUY", 75.0, "MA5 上穿 MA20，站上 MA60")
    notify_risk_mode("NORMAL", "DEFENSIVE")
    notify_daily_report(10000, 250, 65.0, "NORMAL", 1)
    print("完成！請確認 Discord 是否收到訊息。")
