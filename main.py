import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import pytz
from openai import OpenAI

# ============ CONFIG ============
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
BASE_URL = os.getenv("BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()


# ============ OPENAI HELPER ============
def get_openai_client():
    if not OPENAI_API_KEY:
        return None
    return OpenAI(api_key=OPENAI_API_KEY)


async def fetch_league_picks(league: str) -> str:
    """Fetch picks for a specific league from OpenAI."""
    client = get_openai_client()
    if not client:
        return "⚠️ AI not configured. Contact admin."
    
    tz = pytz.timezone("America/Chicago")
    now = datetime.now(tz)
    date_str = now.strftime("%B %d, %Y")
    
    league_prompts = {
        "nba": f"""Today is {date_str}. Give me 3 NBA moneyline underdog picks for today's games.

Format each pick EXACTLY like this:
🏀 [Team Name] ML
💰 Odds: [+XXX]
📊 Confidence: [High/Medium/Low]
📝 [One sentence reason]

Only the picks. No intro or outro.""",

        "nhl": f"""Today is {date_str}. Give me 3 NHL moneyline underdog picks for today's games.

Format each pick EXACTLY like this:
🏒 [Team Name] ML
💰 Odds: [+XXX]
📊 Confidence: [High/Medium/Low]
📝 [One sentence reason]

Only the picks. No intro or outro.""",

        "soccer": f"""Today is {date_str}. Give me 3 soccer moneyline picks for today's major league games.

Format each pick EXACTLY like this:
⚽ [Team Name] ML
💰 Odds: [+XXX or -XXX]
📊 Confidence: [High/Medium/Low]
📝 [One sentence reason]

Only the picks. No intro or outro.""",

        "ncaab": f"""Today is {date_str}. Give me 3 NCAAB moneyline underdog picks for today's games.

Format each pick EXACTLY like this:
🏀 [Team Name] ML
💰 Odds: [+XXX]
📊 Confidence: [High/Medium/Low]
📝 [One sentence reason]

Only the picks. No intro or outro.""",
    }
    
    prompt = league_prompts.get(league.lower())
    if not prompt:
        return "❌ Unknown league."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a sports betting analyst. Give concise, actionable picks."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"


# ============ BASIC COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """🏆 <b>WINNING CIRCLE</b>

Your AI-powered betting intelligence assistant.

<b>Commands:</b>
/picks - View all leagues
/nba - NBA picks
/nhl - NHL picks
/soccer - Soccer picks
/ncaab - College basketball
/help - Show help

<i>For entertainment only. Gamble responsibly.</i>"""
    
    await update.message.reply_text(welcome, parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🏆 <b>WINNING CIRCLE HELP</b>

<b>League Commands:</b>
/nba - NBA moneyline picks
/nhl - NHL moneyline picks
/soccer - Soccer picks
/ncaab - College basketball picks
/picks - Interactive league menu

<b>Other:</b>
/start - Welcome message
/help - This message

<i>Picks are AI-generated for entertainment only.</i>"""
    
    await update.message.reply_text(help_text, parse_mode="HTML")


# ============ LEAGUE COMMANDS ============
async def picks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interactive league selection menu."""
    keyboard = [
        [
            InlineKeyboardButton("🏀 NBA", callback_data="league_nba"),
            InlineKeyboardButton("🏒 NHL", callback_data="league_nhl"),
        ],
        [
            InlineKeyboardButton("⚽ Soccer", callback_data="league_soccer"),
            InlineKeyboardButton("🏀 NCAAB", callback_data="league_ncaab"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏆 <b>WINNING CIRCLE</b>\n\nSelect a league:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def nba_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🏀 Fetching NBA picks...")
    picks = await fetch_league_picks("nba")
    
    text = f"""🏀 <b>NBA PICKS</b>
📅 {datetime.now(pytz.timezone('America/Chicago')).strftime('%B %d, %Y')}
━━━━━━━━━━━━━━━

{picks}

━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    await msg.edit_text(text, parse_mode="HTML")


async def nhl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🏒 Fetching NHL picks...")
    picks = await fetch_league_picks("nhl")
    
    text = f"""🏒 <b>NHL PICKS</b>
📅 {datetime.now(pytz.timezone('America/Chicago')).strftime('%B %d, %Y')}
━━━━━━━━━━━━━━━

{picks}

━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    await msg.edit_text(text, parse_mode="HTML")


async def soccer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⚽ Fetching Soccer picks...")
    picks = await fetch_league_picks("soccer")
    
    text = f"""⚽ <b>SOCCER PICKS</b>
📅 {datetime.now(pytz.timezone('America/Chicago')).strftime('%B %d, %Y')}
━━━━━━━━━━━━━━━

{picks}

━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    await msg.edit_text(text, parse_mode="HTML")


async def ncaab_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🏀 Fetching NCAAB picks...")
    picks = await fetch_league_picks("ncaab")
    
    text = f"""🏀 <b>NCAAB PICKS</b>
📅 {datetime.now(pytz.timezone('America/Chicago')).strftime('%B %d, %Y')}
━━━━━━━━━━━━━━━

{picks}

━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    await msg.edit_text(text, parse_mode="HTML")


# ============ CALLBACK HANDLER ============
async def league_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()
    
    league_map = {
        "league_nba": ("nba", "🏀", "NBA"),
        "league_nhl": ("nhl", "🏒", "NHL"),
        "league_soccer": ("soccer", "⚽", "SOCCER"),
        "league_ncaab": ("ncaab", "🏀", "NCAAB"),
    }
    
    if query.data not in league_map:
        await query.edit_message_text("❌ Unknown selection.")
        return
    
    league, emoji, name = league_map[query.data]
    await query.edit_message_text(f"{emoji} Fetching {name} picks...")
    
    picks = await fetch_league_picks(league)
    
    text = f"""{emoji} <b>{name} PICKS</b>
📅 {datetime.now(pytz.timezone('America/Chicago')).strftime('%B %d, %Y')}
━━━━━━━━━━━━━━━

{picks}

━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    await query.edit_message_text(text, parse_mode="HTML")


# ============ REGISTER HANDLERS ============
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("help", help_cmd))
tg_app.add_handler(CommandHandler("picks", picks_menu))
tg_app.add_handler(CommandHandler("nba", nba_command))
tg_app.add_handler(CommandHandler("nhl", nhl_command))
tg_app.add_handler(CommandHandler("soccer", soccer_command))
tg_app.add_handler(CommandHandler("ncaab", ncaab_command))
tg_app.add_handler(CallbackQueryHandler(league_callback, pattern="^league_"))


# ============ FASTAPI ROUTES ============
@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.start()
    if BASE_URL:
        webhook_url = f"{BASE_URL}/webhook/{WEBHOOK_SECRET}"
        await tg_app.bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set: {webhook_url}")


@app.on_event("shutdown")
async def on_shutdown():
    await tg_app.stop()
    await tg_app.shutdown()


@app.get("/")
async def health():
    return {"status": "ok", "bot": "Winning Circle"}


@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"ok": False}
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
