import logging
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler


# 🔹 Buraya kendi bot tokenini yaz
BOT_TOKEN = "8276797016:AAEaWpIzpgHTYFcI3DXuKx7RLHPbqrQe03g"

CHAT_ID = -1003034219615  

logging.basicConfig(level=logging.INFO)

async def lock_group(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_chat_permissions(
        CHAT_ID,
        ChatPermissions(can_send_messages=False)
    )
    await context.bot.send_message(CHAT_ID, "🔒 Grup kilitlendi (23:00)")

async def unlock_group(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_chat_permissions(
        CHAT_ID,
        ChatPermissions(can_send_messages=True)
    )
    await context.bot.send_message(CHAT_ID, "🔓 Grup açıldı (07:00)")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot çalışıyor! 🔥")

# -------------------------------
# Botu başlat
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

# Scheduler'ı polling başladıktan sonra başlatmak için async fonksiyon
async def run():
    # Scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(lock_group, "cron", hour=23, minute=0, args=[app.bot])
    scheduler.add_job(unlock_group, "cron", hour=7, minute=0, args=[app.bot])
    scheduler.start()
    
    await app.run_polling()

# -------------------------------
import asyncio
asyncio.run(run())
