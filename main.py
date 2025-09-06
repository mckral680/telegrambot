import logging
import os
import asyncio
from datetime import datetime, timedelta

import pytz
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# APScheduler asyncio sürücüsü
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

# --- helper: kilitleme/açma (bot objesi alır) ---
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

# --- scheduler wrappers (bu fonksiyonlar job olarak eklenecek) ---
async def scheduled_lock():
    bot = app.bot
    if bot is None:
        logging.error("Bot nesnesi hazır değil (app.bot is None). Job iptal ediliyor.")
        return
    await lock_group(bot)

async def scheduled_unlock():
    bot = app.bot
    if bot is None:
        logging.error("Bot nesnesi hazır değil (app.bot is None). Job iptal ediliyor.")
        return
    await unlock_group(bot)

# --- HANDLERLAR (komutlar) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔒 Kilitle", callback_data="lock")],
        [InlineKeyboardButton("🔓 Aç", callback_data="unlock")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot çalışıyor! 🔥", reply_markup=reply_markup)

async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kullanıcı komutuyla hemen kilitle
    await lock_group(context.bot)
    await update.message.reply_text("✅ Grup kilitlenme isteği gönderildi.")

async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await unlock_group(context.bot)
    await update.message.reply_text("✅ Grup açılma isteği gönderildi.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "lock":
        await lock_group(context.bot)
        await query.edit_message_text("🔒 Grup kilitlendi (buton ile)")
    elif query.data == "unlock":
        await unlock_group(context.bot)
        await query.edit_message_text("🔓 Grup açıldı (buton ile)")

# --- DEBUG / TEST KOMUTLARI ---
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"This chat id: {update.effective_chat.id}")

async def test_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Hemen kilitle (anında test)
    await lock_group(context.bot)
    await update.message.reply_text("Test: Kilitleme denendi.")

async def schedule_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 30 saniye sonra (lokal timezone) bir job çalıştırıp kilitleme test eder
    tz = pytz.timezone(TZ)
    run_time = datetime.now(tz) + timedelta(seconds=30)
    scheduler.add_job(scheduled_lock, trigger='date', run_date=run_time)
    await update.message.reply_text(f"Test job'u {run_time.isoformat()} tarihinde çalışacak (server TZ={TZ}).")

async def list_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = scheduler.get_jobs()
    if not jobs:
        await update.message.reply_text("Kayıtlı job yok.")
        return
    lines = []
    for j in jobs:
        next_run = j.next_run_time.isoformat() if j.next_run_time else "None"
        lines.append(f"id={j.id}, next_run={next_run}, trigger={j.trigger}")
    await update.message.reply_text("\n".join(lines))

# --- REGISTER HANDLERS ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("lock", lock_cmd))
app.add_handler(CommandHandler("unlock", unlock_cmd))
app.add_handler(CallbackQueryHandler(button_handler))

# debug/test komutları
app.add_handler(CommandHandler("get_chat_id", get_chat_id))
app.add_handler(CommandHandler("test_lock", test_lock))
app.add_handler(CommandHandler("schedule_test", schedule_test))
app.add_handler(CommandHandler("jobs", list_jobs))

# --- SCHEDULER (AsyncIOScheduler kullanıyoruz) ---
scheduler = AsyncIOScheduler(timezone=TZ)

# Örnek cron joblar (senin istediğin zamanları buraya koy)
# scheduler.add_job(scheduled_lock, CronTrigger(hour=23, minute=0))
# scheduler.add_job(scheduled_unlock, CronTrigger(hour=7, minute=0))

# Örnek: debug için yorumdan çıkarabilirsin:
scheduler.add_job(scheduled_lock, CronTrigger(hour=8, minute=51))
scheduler.add_job(scheduled_unlock, CronTrigger(hour=8, minute=53))

scheduler.start()
logging.info("Scheduler started. Current jobs: %s", scheduler.get_jobs())

# --- BAŞLAT ---
if __name__ == "__main__":
    logging.info("Starting bot...")
    app.run_polling()
