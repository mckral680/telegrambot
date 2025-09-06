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

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Örn: -1001234567890
TZ = "Europe/Istanbul"
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))  # Sadece admin kullanabilir

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- GLOBAL SCHEDULER ---
scheduler = AsyncIOScheduler(timezone=timezone(TZ))

# --- Admin-only decorator ---
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != ADMIN_USER_ID:
            if update.callback_query:
                await update.callback_query.answer("❌ Sadece admin kullanabilir.", show_alert=True)
            else:
                await update.message.reply_text("❌ Bu komutu sadece admin kullanabilir.")
            return
        await func(update, context)
    return wrapper

# --- Grup Kilitle / Aç ---
async def lock_group(bot):
    try:
        await bot.set_chat_permissions(CHAT_ID, ChatPermissions(can_send_messages=False))
        await bot.send_message(CHAT_ID, "🔒 Grup kilitlendi")
        logging.info("Group locked successfully")
    except Exception as e:
        logging.exception("Error while locking group: %s", e)

async def unlock_group(bot):
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

@admin_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await lock_group(context.application.bot)
    await update.message.reply_text("✅ Grup kilitlendi (manuel).")

@admin_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await unlock_group(context.application.bot)
    await update.message.reply_text("✅ Grup açıldı (manuel).")

@admin_only
async def schedule_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz = timezone(TZ)
    now = datetime.now(tz)

    # Test jobları async-safe
    async def test_lock():
        await lock_group(context.application.bot)
    async def test_unlock():
        await unlock_group(context.application.bot)

    scheduler.add_job(test_lock, 'date', run_date=now + timedelta(seconds=30))
    scheduler.add_job(test_unlock, 'date', run_date=now + timedelta(seconds=60))

    await update.message.reply_text(
        "✅ Test jobları planlandı: 30 sn sonra kilit, 60 sn sonra aç."
    )

# --- Buton callback ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id != ADMIN_USER_ID:
        await query.answer("❌ Sadece admin kullanabilir.", show_alert=True)
        return

    if query.data == "lock":
        await lock_group(context.application.bot)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context.application.bot)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")

# --- Scheduler ve Cron jobları ---
async def post_init(app):
    # Cron joblar
    async def cron_lock():
        await lock_group(app.bot)
    async def cron_unlock():
        await unlock_group(app.bot)

    scheduler.add_job(cron_lock, CronTrigger(hour=10, minute=53))
    scheduler.add_job(cron_unlock, CronTrigger(hour=10, minute=54))
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

