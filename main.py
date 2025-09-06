import logging
import os
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Environment variable destekli
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))

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

# Bot oluştur
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

# Scheduler (BackgroundScheduler kullanıyoruz)
scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
scheduler.add_job(lambda: app.create_task(lock_group(app)), CronTrigger(hour=23, minute=0))
scheduler.add_job(lambda: app.create_task(unlock_group(app)), CronTrigger(hour=7, minute=0))
scheduler.start()

# Botu başlat (blocking)
app.run_polling()
