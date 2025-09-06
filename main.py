import logging
import os
from pytz import timezone
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Örn: -1001234567890
TZ = "Europe/Istanbul"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- GLOBAL SCHEDULER ---
scheduler = AsyncIOScheduler(timezone=timezone(TZ))

# --- Grup Kilitle / Aç ---
async def lock_group(bot_or_context):
    bot = getattr(bot_or_context, "bot", bot_or_context)
    try:
        await bot.set_chat_permissions(CHAT_ID, ChatPermissions(can_send_messages=False))
        await bot.send_message(CHAT_ID, "🔒 Grup kilitlendi")
        logging.info("Group locked successfully")
    except Exception as e:
        logging.exception("Error while locking group: %s", e)

async def unlock_group(bot_or_context):
    bot = getattr(bot_or_context, "bot", bot_or_context)
    try:
        await bot.set_chat_permissions(CHAT_ID, ChatPermissions(can_send_messages=True))
        await bot.send_message(CHAT_ID, "🔓 Grup açıldı")
        logging.info("Group unlocked successfully")
    except Exception as e:
        logging.exception("Error while unlocking group: %s", e)

# --- Komutlar ve Butonlar ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔒 Kilitle", callback_data="lock")],
        [InlineKeyboardButton("🔓 Aç", callback_data="unlock")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot çalışıyor! 🔥", reply_markup=reply_markup)

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await lock_group(context)
    await update.message.reply_text("✅ Grup kilitlendi (manuel).")

async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await unlock_group(context)
    await update.message.reply_text("✅ Grup açıldı (manuel).")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "lock":
        await lock_group(context)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")

# --- /schedule_test Komutu ---
async def schedule_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz = timezone(TZ)
    now = datetime.now(tz)

    # Asyncio-safe şekilde job ekle
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(lock_group(context.application), context.application.loop),
        trigger='date',
        run_date=now + timedelta(seconds=30)
    )
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(unlock_group(context.application), context.application.loop),
        trigger='date',
        run_date=now + timedelta(seconds=60)
    )

    await update.message.reply_text(
        "✅ Test jobları planlandı: 30 sn sonra kilit, 60 sn sonra aç."
    )

# --- Scheduler ve Cron joblarını bot loop ile başlat ---
async def post_init(app):
    # Cron joblar: saat 23:00 kilitle, 07:00 aç
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(lock_group(app), app.loop),
        CronTrigger(hour=9, minute=47)
    )
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(unlock_group(app), app.loop),
        CronTrigger(hour=9, minute=48)
    )
    scheduler.start()
    logging.info("Scheduler started and cron jobs added.")

# --- BOTU OLUŞTUR ---
app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

# Handler ekle
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("lock", lock_cmd))
app.add_handler(CommandHandler("unlock", unlock_cmd))
app.add_handler(CommandHandler("schedule_test", schedule_test))
app.add_handler(CallbackQueryHandler(button_handler))

# --- BOTU ÇALIŞTIR ---
if __name__ == "__main__":
    logging.info("Bot başlatılıyor...")
    app.run_polling()
