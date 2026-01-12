import os
import requests
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (Render.com compatible)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
API_URL = os.getenv("API_URL", "https://your-render-domain.onrender.com/movies.php")

# Banned users storage (in-memory, Render restarts clear it)
banned_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🎬 **Movie Finder Bot**

Just type any movie or anime name and get instant links!

**Example:** `Avengers End Game`

**Commands:**
/help - Show usage
/report - Report issues
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 **How to use:**

1️⃣ Type movie/anime name: `Spider-Man`
2️⃣ Bot replies with link if found
3️⃣ No link? Try exact name!

**Admin Commands:**
/add <name> | <link>
/ban <user_id>
/unban <user_id>
/admin
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command (ADMIN ONLY)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Better luck next time 😔")
        return
    
    banned_count = len(banned_users)
    admin_text = f"""
🔧 **Admin Panel**

👑 Admin ID: `{ADMIN_USER_ID}`
🚫 Banned Users: `{banned_count}`
📁 API URL: `{API_URL}`

**Commands:**
/add <movie> | <link>
/ban <user_id>
/unban <user_id>
    """
    await update.message.reply_text(admin_text, parse_mode='Markdown')

async def add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command (ADMIN ONLY)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Better luck next time 😔")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Format: `/add Avengers End Game | https://t.me/link`", parse_mode='Markdown')
        return
    
    # Parse arguments
    args = " ".join(context.args)
    if "|" not in args:
        await update.message.reply_text("❌ Format: `/add Avengers End Game | https://t.me/link`", parse_mode='Markdown')
        return
    
    movie_name, link = args.split("|", 1)
    movie_name = movie_name.strip().lower()
    link = link.strip()
    
    # Send to PHP API
    try:
        response = requests.post(API_URL, json={
            "action": "add",
            "movie": movie_name,
            "link": link
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                await update.message.reply_text(f"✅ Added: `{movie_name}`
🔗 `{link}`", parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Error: {result.get('message', 'Unknown error')}")
        else:
            await update.message.reply_text("❌ API Error. Check server.")
    except Exception as e:
        logger.error(f"Add movie error: {e}")
        await update.message.reply_text("❌ Server error. Try again.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban command (ADMIN ONLY)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Better luck next time 😔")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Format: `/ban 123456789`")
        return
    
    try:
        target_id = int(context.args[0])
        banned_users.add(target_id)
        await update.message.reply_text(f"🚫 Banned user: `{target_id}`", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unban command (ADMIN ONLY)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Better luck next time 😔")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Format: `/unban 123456789`")
        return
    
    try:
        target_id = int(context.args[0])
        banned_users.discard(target_id)
        await update.message.reply_text(f"✅ Unbanned user: `{target_id}`", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")

async def report_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "No username"
    first_name = update.effective_user.first_name or "No name"
    
    message_text = update.message.text.replace("/report", "").strip()
    if not message_text:
        await update.message.reply_text("❌ Please describe your issue after /report")
        return
    
    report_msg = f"""
📢 **New Report**

👤 User: `{first_name}` (@{username})
🆔 ID: `{user_id}`
📝 Issue: {message_text}
    """
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=report_msg,
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ Report sent to admin! Thank you 🙏")
    except Exception as e:
        logger.error(f"Report error: {e}")
        await update.message.reply_text("❌ Failed to send report. Try again.")

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages (movie search)"""
    user_id = update.effective_user.id
    
    # Check if banned
    if user_id in banned_users:
        return
    
    text = update.message.text.strip()
    
    # Skip commands and short messages
    if text.startswith("/") or len(text) < 2:
        return
    
    try:
        # Send to PHP API
        response = requests.post(API_URL, json={
            "action": "search",
            "movie": text
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "found":
                link = result["link"]
                username = update.effective_user.username or "User"
                reply_text = f"DRACXONgaming aapka link yeh raha 🔗
{link}"
                await update.message.reply_text(reply_text, disable_web_page_preview=True)
            else:
                await update.message.reply_text("❌ Better luck next time 😔")
        else:
            logger.error(f"API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Better luck next time 😔")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("add", add_movie))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("report", report_issue))
    
    # Movie search (all other text messages)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
    
    # Start bot
    logger.info("Starting Movie Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()