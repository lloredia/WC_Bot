import os
import json
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import pytz
import httpx

# ============ CONFIG ============
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
BASE_URL = os.getenv("BASE_URL")

# GitHub Pages URLs
GITHUB_PAGES_BASE = "https://lloredia.github.io/Winning-circle"
REPORTS_URL = f"{GITHUB_PAGES_BASE}/reports"
BETSLIPS_URL = f"{GITHUB_PAGES_BASE}/betslips"
PICKS_URL = f"{GITHUB_PAGES_BASE}/picks"

app = FastAPI()
tg_app = Application.builder().token(TOKEN).build()


# ============ GITHUB PAGES HELPERS ============
async def get_latest_picks() -> dict | None:
    """Fetch the latest picks JSON from GitHub Pages."""
    try:
        async with httpx.AsyncClient() as client:
            # First get the latest.json pointer
            resp = await client.get(f"{PICKS_URL}/latest.json", timeout=10)
            if resp.status_code != 200:
                return None
            
            latest_info = resp.json()
            picks_file = latest_info.get("latest")
            
            # Then fetch the actual picks
            resp = await client.get(f"{PICKS_URL}/{picks_file}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch picks: {e}")
    return None


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


def format_picks_message(picks: list, league_name: str, emoji: str) -> str:
    """Format picks into a nice Telegram message."""
    tz = pytz.timezone("America/Chicago")
    date_str = datetime.now(tz).strftime('%B %d, %Y')
    
    header = f"""{emoji} <b>{league_name} PICKS</b>
📅 {date_str}
━━━━━━━━━━━━━━━

"""
    
    body = ""
    for pick in picks:
        body += f"<b>{pick.get('pick', 'Unknown')}</b>\n"
        if pick.get('odds'):
            body += f"💰 Odds: {pick.get('odds')}\n"
        if pick.get('confidence'):
            body += f"📊 {pick.get('confidence')} Confidence\n"
        if pick.get('reason'):
            body += f"📝 {pick.get('reason')}\n"
        body += "\n"
    
    footer = """━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    return header + body + footer


# ============ BASIC COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """🏆 <b>WINNING CIRCLE</b>

Your AI-powered betting intelligence assistant.

<b>Commands:</b>
/picks - All today's picks
/slip - Today's bet slip image
/report - Full PDF report
/help - Show help

<i>For entertainment only. Gamble responsibly.</i>"""
    
    await update.message.reply_text(welcome, parse_mode="HTML")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """🏆 <b>WINNING CIRCLE HELP</b>

<b>Commands:</b>
/picks - View all today's picks
/slip - Today's bet slip image
/report - Full PDF report link

<b>Other:</b>
/start - Welcome message
/help - This message

<i>Picks are generated daily at midnight Chicago time.</i>"""
    
    await update.message.reply_text(help_text, parse_mode="HTML")


# ============ PICKS COMMANDS ============
async def picks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all picks from today's report."""
    msg = await update.message.reply_text("🏆 Fetching today's picks...")
    
    picks_data = await get_latest_picks()
    
    if not picks_data:
        await msg.edit_text(
            "❌ No picks available yet.\n\n"
            "Picks are generated at midnight Chicago time.\n"
            "Check back later!"
        )
        return
    
    date_str = picks_data.get("date", "Unknown")
    leagues = picks_data.get("leagues", {})
    
    all_picks_text = f"""🏆 <b>WINNING CIRCLE</b>
📅 {date_str}
━━━━━━━━━━━━━━━

"""
    
    # Add underdog picks (NBA/NHL/NCAAB)
    if "underdog" in leagues:
        all_picks_text += "🎯 <b>NBA / NHL / NCAAB</b>\n\n"
        for pick in leagues["underdog"].get("picks", []):
            all_picks_text += f"• <b>{pick.get('pick', '')}</b>"
            if pick.get('odds'):
                all_picks_text += f" | {pick.get('odds')}"
            if pick.get('confidence'):
                all_picks_text += f" | {pick.get('confidence')}"
            all_picks_text += "\n"
        all_picks_text += "\n"
    
    # Add soccer picks
    if "soccer" in leagues:
        all_picks_text += "⚽ <b>SOCCER</b>\n\n"
        for pick in leagues["soccer"].get("picks", []):
            all_picks_text += f"• <b>{pick.get('pick', '')}</b>"
            if pick.get('odds'):
                all_picks_text += f" | {pick.get('odds')}"
            if pick.get('confidence'):
                all_picks_text += f" | {pick.get('confidence')}"
            all_picks_text += "\n"
        all_picks_text += "\n"
    
    all_picks_text += """━━━━━━━━━━━━━━━
<i>For entertainment only.</i>"""
    
    # Add buttons for slip and report
    keyboard = []
    
    betslip_url = await get_todays_betslip_url()
    report_url = await get_latest_report_url()
    
    if betslip_url or report_url:
        row = []
        if betslip_url:
            row.append(InlineKeyboardButton("🎫 Bet Slip", callback_data="show_slip"))
        if report_url:
            row.append(InlineKeyboardButton("📄 PDF Report", url=report_url))
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await msg.edit_text(all_picks_text, parse_mode="HTML", reply_markup=reply_markup)


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
            "Use /picks to see if picks are available."
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
            keyboard.append([InlineKeyboardButton("🎫 View Bet Slip", callback_data="show_slip")])
        
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
            "Use /picks to see if picks are available."
        )


# ============ CALLBACK HANDLER ============
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_slip":
        betslip_url = await get_todays_betslip_url()
        
        if betslip_url:
            tz = pytz.timezone("America/Chicago")
            today = datetime.now(tz).strftime("%B %d, %Y")
            
            await query.message.reply_photo(
                photo=betslip_url,
                caption=f"🏆 <b>WINNING CIRCLE</b>\n📅 {today}",
                parse_mode="HTML"
            )
        else:
            await query.answer("No bet slip available yet.", show_alert=True)
    
    else:
        await query.answer("Unknown action.", show_alert=True)


# ============ REGISTER HANDLERS ============
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("help", help_cmd))
tg_app.add_handler(CommandHandler("picks", picks_command))
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


@app.get("/debug/picks")
async def debug_picks():
    """Debug endpoint to check picks data."""
    picks_data = await get_latest_picks()
    return {
        "picks_available": picks_data is not None,
        "data": picks_data
    }


@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return {"ok": False}
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
