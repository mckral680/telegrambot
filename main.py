import logging
import os
from pytz import timezone
from datetime import datetime
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
TZ = "Europe/Istanbul"
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

scheduler = AsyncIOScheduler(timezone=timezone(TZ))

# Varsayılan saatler
lock_hour = 11
lock_minute = 10
unlock_hour = 11
unlock_minute = 11

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

# --- Kilitle / Aç fonksiyonları ---
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

# --- Scheduler update ---
async def update_scheduler(bot):
    scheduler.remove_all_jobs()

    async def cron_lock():
        await lock_group(bot)
        logging.info("Cron Lock çalıştı ✅")

    async def cron_unlock():
        await unlock_group(bot)
        logging.info("Cron Unlock çalıştı ✅")

    scheduler.add_job(cron_lock, CronTrigger(hour=lock_hour, minute=lock_minute, timezone=timezone(TZ)))
    scheduler.add_job(cron_unlock, CronTrigger(hour=unlock_hour, minute=unlock_minute, timezone=timezone(TZ)))
    logging.info(f"Cron joblar ayarlandı: Kilitle {lock_hour:02d}:{lock_minute:02d}, Aç {unlock_hour:02d}:{unlock_minute:02d}")

# --- Start ve buton menüsü ---
@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔒 Grubu kilitle", callback_data="lock")],
        [InlineKeyboardButton("🔓 Kilidi aç", callback_data="unlock")],
        [InlineKeyboardButton("⏰ Saatleri ayarla", callback_data="set_time")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot hazır! Bir işlem seçin:", reply_markup=reply_markup)

# --- Dinamik saat ayarlama ---
LOCK_HOUR, LOCK_MINUTE, UNLOCK_HOUR, UNLOCK_MINUTE = range(4)

def get_reply_target(update: Update):
    """Callback query’den geliyorsa message objesini al, değilse update.message kullan."""
    if update.message:
        return update.message
    elif update.callback_query:
        return update.callback_query.message
    return None

async def set_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_reply_target(update)
    if target:
        await target.reply_text("Kilitleme saati için saat (0-23) girin:")
    return LOCK_HOUR

async def get_lock_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global lock_hour
    target = get_reply_target(update)
    try:
        lock_hour = int(update.message.text)
        if not 0 <= lock_hour <= 23:
            raise ValueError
        await target.reply_text("Kilitleme dakikası (0-59) girin:")
        return LOCK_MINUTE
    except:
        await target.reply_text("❌ 0-23 arası bir sayı girin.")
        return LOCK_HOUR

async def get_lock_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global lock_minute
    target = get_reply_target(update)
    try:
        lock_minute = int(update.message.text)
        if not 0 <= lock_minute <= 59:
            raise ValueError
        await target.reply_text("Açma saati için saat (0-23) girin:")
        return UNLOCK_HOUR
    except:
        await target.reply_text("❌ 0-59 arası bir sayı girin.")
        return LOCK_MINUTE

async def get_unlock_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global unlock_hour
    target = get_reply_target(update)
    try:
        unlock_hour = int(update.message.text)
        if not 0 <= unlock_hour <= 23:
            raise ValueError
        await target.reply_text("Açma dakikası (0-59) girin:")
        return UNLOCK_MINUTE
    except:
        await target.reply_text("❌ 0-23 arası bir sayı girin.")
        return UNLOCK_HOUR

async def get_unlock_minute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global unlock_minute
    target = get_reply_target(update)
    try:
        unlock_minute = int(update.message.text)
        if not 0 <= unlock_minute <= 59:
            raise ValueError

        # Scheduler güncelle
        await update_scheduler(context.application.bot)

        await target.reply_text(
            f"✅ Saatler ayarlandı!\nKilitleme: {lock_hour:02d}:{lock_minute:02d}\nAçma: {unlock_hour:02d}:{unlock_minute:02d}"
        )
        return ConversationHandler.END
    except:
        await target.reply_text("❌ 0-59 arası bir sayı girin.")
        return UNLOCK_MINUTE


# --- Buton callback ---
@admin_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "lock":
        await lock_group(context.application.bot)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context.application.bot)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")
    elif query.data == "set_time":
        await query.edit_message_text("⏰ Saatleri ayarlamaya başlıyoruz...")
        # Dinamik input için adım başlat
        await set_time_start(update, context)

# --- Conversation Handler ---
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler, pattern="^set_time$")],
    states={
        LOCK_HOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lock_hour)],
        LOCK_MINUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lock_minute)],
        UNLOCK_HOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_unlock_hour)],
        UNLOCK_MINUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_unlock_minute)],
    },
    fallbacks=[]
)

# --- Scheduler post_init ---
async def post_init(app):
    scheduler.start()
    logging.info("Scheduler başlatıldı.")

# --- BOTU OLUŞTUR ---
app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

# Handler ekle
app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)

# --- BOTU ÇALIŞTIR ---
if __name__ == "__main__":
    logging.info("Bot başlatılıyor...")
    app.run_polling()


