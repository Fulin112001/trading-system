import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))
import discord
from discord.ext import commands
from discord.bot import handle_command

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Discord Bot 啟動：{bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🤖 Fulin Trading Bot 已上線！輸入 `!help` 查看指令")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id != CHANNEL_ID:
        return
    if not message.content.startswith("!"):
        return
    print(f"收到指令：{message.content}")
    handle_command(WEBHOOK, message.content)
    await bot.process_commands(message)

def run_bot():
    if not TOKEN:
        print("❌ 請設定 DISCORD_BOT_TOKEN")
        return
    print("🤖 啟動 Discord Bot...")
    bot.run(TOKEN)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ 請設定 DISCORD_BOT_TOKEN")
    else:
        print("🤖 啟動 Discord Bot...")
        bot.run(TOKEN)
