import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import pytz
from openai import OpenAI
import httpx

# ============ CONFIG ============
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
BASE_URL = os.getenv("BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GitHub Pages URLs
GITHUB_PAGES_BASE = "https://lloredia.github.io/Winning-circle"
REPORTS_URL = f"{GITHUB_PAGES_BASE}/reports"
BETSLIPS_URL = f"{GITHUB_PAGES_BASE}/betslips"

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()


# ============ GITHUB PAGES HELPERS ============
async def get_latest_report_url() -> str | None:
    """Fetch the latest report filename from GitHub Pages."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{REPORTS_URL}/latest.txt", timeout=10)
            if resp.status_code == 200:
                filename = resp.text.strip()
                return f"{REPORTS_URL}/{filename}"
    except Exception as e:
        print(f"[ERROR] Failed to fetch latest report: {e}")
    return None


async def get_todays_betslip_url() -> str | None:
    """Get today's bet slip image URL."""
    tz = pytz.timezone("America/Chicago")
    today = datetime.now(tz).strftime("%Y-%m-%d")
    betslip_url = f"{BETSLIPS_URL}/betslip_{today}.png"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.head(betslip_url, timeout=10)
            if resp.status_code == 200:
                return betslip_url
    except Exception as e:
        print(f"[ERROR] Failed to check betslip: {e}")
    return None


# ============ OPENAI HELPER ============
async def fetch_league_picks(league: str) -> str:
    """Fetch picks for a specific league from OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
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
        client = OpenAI(api_key=api_key)
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
        error_msg = str(e)
        print(f"[OPENAI ERROR] {error_msg}")
        return f"⚠️ Error: {error_msg[:100]}"


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
/slip - Today's bet slip image
/report - Full PDF report
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

<b>Reports:</b>
/slip - Today's bet slip image
/report - Full PDF report link

<b>Other:</b>
/start - Welcome message
/help - This message

<i>Picks are AI-generated for entertainment only.</i>"""
    
    await update.message.reply_text(help_text, parse_mode="HTML")


# ============ REPORT COMMANDS ============
async def slip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send today's bet slip image."""
    msg = await update.message.reply_text("🎫 Fetching today's bet slip...")
    
    betslip_url = await get_todays_betslip_url()
    report_url = await get_latest_report_url()
    
    if betslip_url:
        tz = pytz.timezone("America/Chicago")
        today = datetime.now(tz).strftime("%B %d, %Y")
        
        caption = f"""🏆 <b>WINNING CIRCLE</b>
📅 {today}

"""
        if report_url:
            caption += f"📄 <a href='{report_url}'>View Full Report</a>"
        
        await msg.delete()
        await update.message.reply_photo(
            photo=betslip_url,
            caption=caption,
            parse_mode="HTML"
        )
    else:
        await msg.edit_text(
            "❌ No bet slip available for today yet.\n\n"
            "Bet slips are generated at midnight Chicago time.\n"
            "Use /picks to get live AI picks instead."
        )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send link to latest PDF report."""
    msg = await update.message.reply_text("📄 Fetching latest report...")
    
    report_url = await get_latest_report_url()
    betslip_url = await get_todays_betslip_url()
    
    if report_url:
        tz = pytz.timezone("America/Chicago")
        today = datetime.now(tz).strftime("%B %d, %Y")
        
        keyboard = [[InlineKeyboardButton("📄 Open PDF Report", url=report_url)]]
        
        if betslip_url:
            keyboard.append([InlineKeyboardButton("🎫 View Bet Slip", url=betslip_url)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await msg.edit_text(
            f"""🏆 <b>WINNING CIRCLE</b>
📅 {today}

Your daily report is ready!

Click below to view:""",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    else:
        await msg.edit_text(
            "❌ No report available yet.\n\n"
            "Reports are generated at midnight Chicago time.\n"
            "Use /picks to get live AI picks instead."
        )


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
        [
            InlineKeyboardButton("🎫 Today's Slip", callback_data="show_slip"),
            InlineKeyboardButton("📄 Full Report", callback_data="show_report"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏆 <b>WINNING CIRCLE</b>\n\nSelect an option:",
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
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()
    
    # League selections
    league_map = {
        "league_nba": ("nba", "🏀", "NBA"),
        "league_nhl": ("nhl", "🏒", "NHL"),
        "league_soccer": ("soccer", "⚽", "SOCCER"),
        "league_ncaab": ("ncaab", "🏀", "NCAAB"),
    }
    
    if query.data in league_map:
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
    
    elif query.data == "show_slip":
        await query.edit_message_text("🎫 Fetching bet slip...")
        betslip_url = await get_todays_betslip_url()
        
        if betslip_url:
            await query.message.reply_photo(
                photo=betslip_url,
                caption="🏆 <b>Today's Bet Slip</b>",
                parse_mode="HTML"
            )
            await query.delete_message()
        else:
            await query.edit_message_text("❌ No bet slip available for today yet.")
    
    elif query.data == "show_report":
        report_url = await get_latest_report_url()
        
        if report_url:
            keyboard = [[InlineKeyboardButton("📄 Open PDF Report", url=report_url)]]
            await query.edit_message_text(
                "🏆 <b>WINNING CIRCLE</b>\n\nClick to view your report:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text("❌ No report available yet.")
    
    else:
        await query.edit_message_text("❌ Unknown selection.")


# ============ REGISTER HANDLERS ============
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("help", help_cmd))
tg_app.add_handler(CommandHandler("picks", picks_menu))
tg_app.add_handler(CommandHandler("nba", nba_command))
tg_app.add_handler(CommandHandler("nhl", nhl_command))
tg_app.add_handler(CommandHandler("soccer", soccer_command))
tg_app.add_handler(CommandHandler("ncaab", ncaab_command))
tg_app.add_handler(CommandHandler("slip", slip_command))
tg_app.add_handler(CommandHandler("report", report_command))
tg_app.add_handler(CallbackQueryHandler(button_callback))


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


@app.get("/test-openai")
async def test_openai():
    """Test endpoint to debug OpenAI connection."""
    import traceback
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"error": "No OPENAI_API_KEY found in environment"}
    
    return_data = {
        "api_key_found": True,
        "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "too_short",
        "api_key_length": len(api_key)
    }
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say hello in 5 words"}],
            max_tokens=20
        )
        return_data["success"] = True
        return_data["response"] = response.choices[0].message.content
    except Exception as e:
        return_data["success"] = False
        return_data["error_type"] = type(e).__name__
        return_data["error"] = str(e)
        return_data["traceback"] = traceback.format_exc()
    
    return return_data


@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"ok": False}
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
