import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import requests
import json
from datetime import datetime

API = "http://localhost:8000/api"

def call_api(path, method="GET", body=None):
    try:
        opts = {"headers": {"Content-Type": "application/json"}}
        if body:
            opts["json"] = body
        if method == "GET":
            res = requests.get(API + path, **opts, timeout=10)
        elif method == "POST":
            res = requests.post(API + path, **opts, timeout=10)
        elif method == "DELETE":
            res = requests.delete(API + path, **opts, timeout=10)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def send_discord(webhook, message, title=None, color=0x4f8ef7):
    payload = {"embeds": [{"description": message, "timestamp": datetime.utcnow().isoformat()}]}
    if title: payload["embeds"][0]["title"] = title
    if color: payload["embeds"][0]["color"] = color
    requests.post(webhook, json=payload)

def handle_command(webhook, command):
    cmd = command.strip().lower()

    # !help
    if cmd == "!help":
        send_discord(webhook,
            "**!status** — 系統狀態總覽\n"
            "**!risk** — 風控模式與資金狀態\n"
            "**!portfolio** — 目前持倉\n"
            "**!market** — 市場快照\n"
            "**!stop** — 緊急停止所有交易\n"
            "**!pause** — 暫停交易（保留倉位）\n"
            "**!resume** — 恢復正常交易\n"
            "**!report** — 產出 Excel 報表\n"
            "**!help** — 顯示指令清單",
            title="📋 指令清單", color=0x4f8ef7
        )

    # !status
    elif cmd == "!status":
        data = call_api("/status")
        if "error" in data:
            send_discord(webhook, f"❌ 無法連線：{data['error']}", title="系統狀態")
            return
        risk = data["risk"]
        mode_emoji = "✅" if risk["mode"] == "NORMAL" else "⚠️" if risk["mode"] == "DEFENSIVE" else "🔴"
        send_discord(webhook,
            f"**券商：** {data['broker_name']} ({data['market']})\n"
            f"**風控模式：** {mode_emoji} {risk['mode']}\n"
            f"**可用資金：** ${risk['capital']:,.2f}\n"
            f"**今日損益：** {'🟢 +' if risk['daily_pnl']>=0 else '🔴 '}${abs(risk['daily_pnl']):,.2f}\n"
            f"**連敗次數：** {risk['consecutive_losses']}\n"
            f"**可以交易：** {'是' if risk['can_trade'] else '否'}\n"
            f"**時間：** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            title="📊 系統狀態", color=0x4f8ef7
        )

    # !risk
    elif cmd == "!risk":
        risk = call_api("/risk/status")
        mode_color = 0x00ff88 if risk["mode"]=="NORMAL" else 0xffe033 if risk["mode"]=="DEFENSIVE" else 0xff1a4b
        send_discord(webhook,
            f"**模式：** {risk['mode']}\n"
            f"**資金：** ${risk['capital']:,.2f}\n"
            f"**今日損益：** {'+'if risk['daily_pnl']>=0 else ''}${risk['daily_pnl']:,.2f}\n"
            f"**連敗次數：** {risk['consecutive_losses']}\n"
            f"**總回撤：** {risk['total_drawdown']:.1f}%\n"
            f"**緊急停止：** {'已啟動 🔴' if risk['emergency_stop'] else '未啟動 ✅'}",
            title="🛡️ 風控狀態", color=mode_color
        )

    # !portfolio
    elif cmd == "!portfolio":
        tw = call_api("/portfolio/tw_stock")
        crypto = call_api("/portfolio/crypto")
        msg = "**🇹🇼 台股零股組合**\n"
        msg += f"可用資金：${tw['available_capital']:,.0f}　未實現：{'+'if tw['unrealized_pnl']>=0 else ''}${tw['unrealized_pnl']:,.2f}\n"
        if tw.get("positions"):
            for p in tw["positions"]:
                up = p["unrealized_pnl"] >= 0
                msg += f"• {p['symbol']}　現價 ${p['current_price']}　{'🟢 +' if up else '🔴 '}${abs(p['unrealized_pnl']):.2f}\n"
        else:
            msg += "目前無持倉\n"
        msg += f"\n**💰 加密貨幣組合**\n"
        msg += f"可用資金：${crypto['available_capital']:,.0f}　未實現：{'+'if crypto['unrealized_pnl']>=0 else ''}${crypto['unrealized_pnl']:,.2f}\n"
        if crypto.get("positions"):
            for p in crypto["positions"]:
                up = p["unrealized_pnl"] >= 0
                msg += f"• {p['symbol']}　現價 ${p['current_price']}　{'🟢 +' if up else '🔴 '}${abs(p['unrealized_pnl']):.2f}\n"
        else:
            msg += "目前無持倉\n"
        send_discord(webhook, msg, title="💼 投資組合", color=0x4f8ef7)

    # !market
    elif cmd == "!market":
        snap = call_api("/market/snapshot")
        lines = []
        if snap.get("tw_stocks"):
            lines.append("**🇹🇼 台股**")
            for sym, d in snap["tw_stocks"].items():
                arrow = "▲" if d["change_pct"]>=0 else "▼"
                lines.append(f"{d['name']}　${d['price']:,.0f}　{arrow} {d['change_pct']:+.2f}%")
        if snap.get("crypto"):
            lines.append("\n**💰 加密貨幣**")
            for cid, d in snap["crypto"].items():
                arrow = "▲" if d["change_pct"]>=0 else "▼"
                lines.append(f"{d['name']}　${d['price']:,.0f}　{arrow} {d['change_pct']:+.2f}%")
        if snap.get("us_etf"):
            lines.append("\n**🌍 美股 ETF**")
            for sym, d in snap["us_etf"].items():
                arrow = "▲" if d["change_pct"]>=0 else "▼"
                lines.append(f"{d['name']}　${d['price']:,.0f}　{arrow} {d['change_pct']:+.2f}%")
        send_discord(webhook, "\n".join(lines), title="📈 市場快照", color=0x4f8ef7)

    # !stop
    elif cmd == "!stop":
        call_api("/risk/emergency-stop", "POST")
        send_discord(webhook,
            f"緊急停止已啟動\n時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n所有新交易已暫停",
            title="🚨 緊急停止", color=0xff1a4b
        )

    # !pause
    elif cmd == "!pause":
        call_api("/risk/pause", "POST")
        send_discord(webhook,
            f"交易已暫停，現有倉位保留\n時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            title="⏸ 暫停交易", color=0xffe033
        )

    # !resume
    elif cmd == "!resume":
        call_api("/risk/resume", "POST")
        send_discord(webhook,
            f"已恢復正常交易\n時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            title="▶ 恢復交易", color=0x00ff88
        )

    # !report
    elif cmd == "!report":
        send_discord(webhook, "產出報表中...", title="📊 Excel 報表")
        try:
            from backend.exporter import export_and_notify
            export_and_notify()
        except Exception as e:
            send_discord(webhook, f"報表產出失敗：{e}", title="❌ 錯誤", color=0xff1a4b)

    else:
        send_discord(webhook,
            f"未知指令：`{command}`\n輸入 `!help` 查看所有指令",
            title="❓ 未知指令", color=0xffe033
        )

def poll_discord(webhook_url, bot_token, channel_id):
    """
    輪詢 Discord 頻道訊息
    需要 Bot Token 才能讀取訊息
    """
    headers = {"Authorization": f"Bot {bot_token}"}
    last_message_id = None
    print(f"🤖 Discord Bot 啟動，監聽頻道 {channel_id}")
    import time
    while True:
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=1"
            if last_message_id:
                url += f"&after={last_message_id}"
            res = requests.get(url, headers=headers, timeout=10)
            messages = res.json()
            if isinstance(messages, list) and messages:
                for msg in reversed(messages):
                    last_message_id = msg["id"]
                    content = msg.get("content", "").strip()
                    if content.startswith("!"):
                        print(f"收到指令：{content}")
                        handle_command(webhook_url, content)
        except Exception as e:
            print(f"Bot 錯誤：{e}")
        time.sleep(3)

if __name__ == "__main__":
    import sys
    from backend.config import get_notification_config
    config = get_notification_config()
    webhook = config.get("discord_webhook", "")
    if not webhook:
        print("❌ 請先設定 discord_webhook")
        sys.exit(1)
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(f"執行指令：{cmd}")
        handle_command(webhook, cmd)
    else:
        print("用法：python discord/bot.py !指令")
        print("例如：python discord/bot.py !status")
        print("例如：python discord/bot.py !market")
