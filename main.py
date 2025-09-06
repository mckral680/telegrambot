import logging
import os
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
# Environment variable destekli
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
print("BOT_TOKEN:", os.environ.get("BOT_TOKEN"))
print("CHAT_ID:", os.environ.get("CHAT_ID"))

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

# Bot oluştur
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Komut handler ekle
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("lock", lock_cmd))
app.add_handler(CommandHandler("unlock", unlock_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

# Scheduler (BackgroundScheduler kullanıyoruz)
scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
scheduler.add_job(lambda: app.create_task(lock_group(app)), CronTrigger(hour=23, minute=0))
scheduler.add_job(lambda: app.create_task(unlock_group(app)), CronTrigger(hour=7, minute=0))
scheduler.start()

# Botu başlat (blocking)
app.run_polling()

