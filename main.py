import logging
import os
from datetime import datetime, timedelta

import pytz
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))  # örn: -1001234567890
TZ = "Europe/Istanbul"

# --- LOG ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- APP ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- SCHEDULER ---
scheduler = AsyncIOScheduler(timezone=TZ)

# Grup kilitle
async def lock_group(bot):
    try:
        await bot.set_chat_permissions(
            CHAT_ID,
            ChatPermissions(can_send_messages=False)
        )
        await bot.send_message(CHAT_ID, "🔒 Grup kilitlendi")
        logging.info("Group locked successfully")
    except Exception as e:
        logging.exception("Error while locking group: %s", e)

# Grup aç
async def unlock_group(bot):
    try:
        await bot.set_chat_permissions(
            CHAT_ID,
            ChatPermissions(can_send_messages=True)
        )
        await bot.send_message(CHAT_ID, "🔓 Grup açıldı")
        logging.info("Group unlocked successfully")
    except Exception as e:
        logging.exception("Error while unlocking group: %s", e)

# Job wrapper fonksiyonları
async def scheduled_lock():
    await lock_group(app.bot)

async def scheduled_unlock():
    await unlock_group(app.bot)

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔒 Kilitle", callback_data="lock")],
        [InlineKeyboardButton("🔓 Aç", callback_data="unlock")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot çalışıyor! 🔥", reply_markup=reply_markup)

# /lock komutu
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await lock_group(context.bot)
    await update.message.reply_text("✅ Grup kilitlendi (manuel komut).")

# /unlock komutu
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await unlock_group(context.bot)
    await update.message.reply_text("✅ Grup açıldı (manuel komut).")

# Buton callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "lock":
        await lock_group(context.bot)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context.bot)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")

# --- HANDLERS EKLE ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("lock", lock_cmd))
app.add_handler(CommandHandler("unlock", unlock_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

# --- post_init (scheduler burada başlatılacak) ---
async def on_startup(app):
    # Cron jobları buraya ekle
    scheduler.add_job(scheduled_lock, CronTrigger(hour=8, minute=57))   # 23:00 kilitle
    scheduler.add_job(scheduled_unlock, CronTrigger(hour=8, minute=58))  # 07:00 aç

    scheduler.start()
    logging.info("Scheduler started. Jobs: %s", scheduler.get_jobs())

# Botu post_init ile başlat
app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

if __name__ == "__main__":
    logging.info("Starting bot...")
    app.run_polling()

