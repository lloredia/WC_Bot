import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
BASE_URL = os.getenv("BASE_URL")  # set after Railway gives you a public URL

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Winning Circle is online. Try /help")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Commands: /start /help /picks")

async def picks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Picks coming soon (AI hook goes here).")

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("help", help_cmd))
tg_app.add_handler(CommandHandler("picks", picks))

@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.start()

    # set Telegram webhook once the app has a public URL
    if BASE_URL:
        webhook_url = f"{BASE_URL}/webhook/{WEBHOOK_SECRET}"
        await tg_app.bot.set_webhook(url=webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    await tg_app.stop()
    await tg_app.shutdown()

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"ok": False}

    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
