import logging
import os
from pytz import timezone
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Örn: -1001234567890
TZ = "Europe/Istanbul"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Kilitleme / Açma Fonksiyonları ---
async def lock_group(bot_or_context):
    bot = getattr(bot_or_context, "bot", bot_or_context)  # context veya bot objesi alabilir
    try:
        await bot.set_chat_permissions(
            CHAT_ID,
            ChatPermissions(can_send_messages=False)
        )
        await bot.send_message(CHAT_ID, "🔒 Grup kilitlendi")
        logging.info("Group locked successfully")
    except Exception as e:
        logging.exception("Error while locking group: %s", e)

async def unlock_group(bot_or_context):
    bot = getattr(bot_or_context, "bot", bot_or_context)
    try:
        await bot.set_chat_permissions(
            CHAT_ID,
            ChatPermissions(can_send_messages=True)
        )
        await bot.send_message(CHAT_ID, "🔓 Grup açıldı")
        logging.info("Group unlocked successfully")
    except Exception as e:
        logging.exception("Error while unlocking group: %s", e)

# --- Komutlar / Butonlar ---
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

# --- Scheduler Başlatma ---
async def start_scheduler(app: Application):
    scheduler = AsyncIOScheduler(timezone=timezone(TZ))
    scheduler.add_job(lambda: app.create_task(lock_group(app)), CronTrigger(hour=23, minute=0))
    scheduler.add_job(lambda: app.create_task(unlock_group(app)), CronTrigger(hour=7, minute=0))
    scheduler.start()
    logging.info("Scheduler started. Jobs: %s", scheduler.get_jobs())

# --- Bot Oluştur ve Handler Eklenir ---
app = ApplicationBuilder().token(BOT_TOKEN).post_init(start_scheduler).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("lock", lock_cmd))
app.add_handler(CommandHandler("unlock", unlock_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

# --- Botu Başlat ---
if __name__ == "__main__":
    logging.info("Bot başlatılıyor...")
    app.run_polling()
import logging
import os
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# Environment variable destekli
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
print("BOT_TOKEN:", BOT_TOKEN)
print("CHAT_ID:", CHAT_ID)

logging.basicConfig(level=logging.INFO)

# Grup kilitle
async def lock_group(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_chat_permissions(
        CHAT_ID,
        ChatPermissions(can_send_messages=False)
    )
    await context.bot.send_message(
        CHAT_ID,
        "🔒 Grup kilitlendi"
    )

# Grup aç
async def unlock_group(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_chat_permissions(
        CHAT_ID,
        ChatPermissions(can_send_messages=True)
    )
    await context.bot.send_message(
        CHAT_ID,
        "🔓 Grup açıldı"
    )

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
    await lock_group(context)

# /unlock komutu
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await unlock_group(context)

# Buton callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "lock":
        await lock_group(context)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")

# Main fonksiyonu
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Komut handler ekle
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Scheduler (AsyncIOScheduler kullanıyoruz)
    scheduler = AsyncIOScheduler(timezone=timezone("Europe/Istanbul"))
    scheduler.add_job(lambda: app.create_task(lock_group(app)), CronTrigger(hour=9, minute=5))
    scheduler.add_job(lambda: app.create_task(unlock_group(app)), CronTrigger(hour=9, minute=6))
    scheduler.start()

    # Botu başlat (tek instance)
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

