import logging
import os
from pytz import timezone
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

# --- Kilitle / Aç ---
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

# --- Saat seçme fonksiyonları ---
def build_time_keyboard(current: int, max_val: int, prefix: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⬆️ {current}", callback_data=f"{prefix}_inc"),
         InlineKeyboardButton(f"⬇️ {current}", callback_data=f"{prefix}_dec")],
        [InlineKeyboardButton("✅ Onayla", callback_data=f"{prefix}_ok")]
    ])

async def time_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Başlat
    if query.data == "set_time":
        await query.edit_message_text(
            f"Kilitleme saati seç: {lock_hour:02d}",
            reply_markup=build_time_keyboard(lock_hour, 23, "lock_hour")
        )

    # LOCK HOUR
    elif query.data.startswith("lock_hour"):
        global lock_hour
        if "_inc" in query.data:
            lock_hour = (lock_hour + 1) % 24
        elif "_dec" in query.data:
            lock_hour = (lock_hour - 1) % 24
        elif "_ok" in query.data:
            await query.edit_message_text(
                f"Kilitleme dakikasını seç: {lock_minute:02d}",
                reply_markup=build_time_keyboard(lock_minute, 59, "lock_minute")
            )
            return
        await query.edit_message_text(
            f"Kilitleme saati seç: {lock_hour:02d}",
            reply_markup=build_time_keyboard(lock_hour, 23, "lock_hour")
        )

    # LOCK MINUTE
    elif query.data.startswith("lock_minute"):
        global lock_minute
        if "_inc" in query.data:
            lock_minute = (lock_minute + 1) % 60
        elif "_dec" in query.data:
            lock_minute = (lock_minute - 1) % 60
        elif "_ok" in query.data:
            await query.edit_message_text(
                f"Açma saati seç: {unlock_hour:02d}",
                reply_markup=build_time_keyboard(unlock_hour, 23, "unlock_hour")
            )
            return
        await query.edit_message_text(
            f"Kilitleme dakikası seç: {lock_minute:02d}",
            reply_markup=build_time_keyboard(lock_minute, 59, "lock_minute")
        )

    # UNLOCK HOUR
    elif query.data.startswith("unlock_hour"):
        global unlock_hour
        if "_inc" in query.data:
            unlock_hour = (unlock_hour + 1) % 24
        elif "_dec" in query.data:
            unlock_hour = (unlock_hour - 1) % 24
        elif "_ok" in query.data:
            await query.edit_message_text(
                f"Açma dakikası seç: {unlock_minute:02d}",
                reply_markup=build_time_keyboard(unlock_minute, 59, "unlock_minute")
            )
            return
        await query.edit_message_text(
            f"Açma saati seç: {unlock_hour:02d}",
            reply_markup=build_time_keyboard(unlock_hour, 23, "unlock_hour")
        )

    # UNLOCK MINUTE
    elif query.data.startswith("unlock_minute"):
        global unlock_minute
        if "_inc" in query.data:
            unlock_minute = (unlock_minute + 1) % 60
        elif "_dec" in query.data:
            unlock_minute = (unlock_minute - 1) % 60
        elif "_ok" in query.data:
            # Scheduler güncelle
            await update_scheduler(context.application.bot)
            await query.edit_message_text(
                f"✅ Saatler ayarlandı!\nKilitleme: {lock_hour:02d}:{lock_minute:02d}\nAçma: {unlock_hour:02d}:{unlock_minute:02d}"
            )
            return
        await query.edit_message_text(
            f"Açma dakikası seç: {unlock_minute:02d}",
            reply_markup=build_time_keyboard(unlock_minute, 59, "unlock_minute")
        )

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
    else:
        await time_selector(update, context)

# --- Scheduler post_init ---
async def post_init(app):
    scheduler.start()
    logging.info("Scheduler başlatıldı.")

# --- BOTU OLUŞTUR ---
app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

# Handler ekle
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

# --- BOTU ÇALIŞTIR ---
if __name__ == "__main__":
    logging.info("Bot başlatılıyor...")
    app.run_polling()
