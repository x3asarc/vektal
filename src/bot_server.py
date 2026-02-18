import os
import logging
import subprocess
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Import Telegram libs (Check if installed first, handled by agent)
try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
except ImportError:
    print("Error: python-telegram-bot is not installed. Please run: pip install python-telegram-bot")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /start command.
    Captures the Chat ID and saves it to .env if not present.
    """
    chat_id = update.effective_chat.id
    user_first_name = update.effective_user.first_name
    
    msg = f"Hello {user_first_name}! 👋\n\nYour Chat ID is: `{chat_id}`\n"
    
    # Auto-save to .env logic
    env_path = ".env"
    try:
        current_env = {}
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                current_env = {line.split("=", 1)[0].strip(): line.strip() for line in lines if "=" in line}
        
        # Check if we need to add the ID
        if "TELEGRAM_CHAT_ID" not in current_env:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write(f"\nTELEGRAM_CHAT_ID={chat_id}\n")
            msg += "\n✅ **Configuration Auto-Saved!**\nI have added your Chat ID to the `.env` file.\nYou can now use /run to control the scraper."
        else:
            saved_id = current_env["TELEGRAM_CHAT_ID"].split("=")[1].strip()
            if str(saved_id) == str(chat_id):
                msg += "\n✅ **System Ready.**\nYour ID matches the configuration."
            else:
                msg += f"\n⚠️ **Config Mismatch**\nThe saved ID is `{saved_id}` but you are `{chat_id}`."
    
    except Exception as e:
        msg += f"\n❌ Error saving config: {str(e)}"
        logging.error(f"Error saving .env: {e}")

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

async def run_scraper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /run command.
    Triggers the image_scraper.py script.
    """
    chat_id = update.effective_chat.id
    
    # Reload env to ensure we have the latest (in case it was just set)
    load_dotenv(override=True)
    allowed_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if str(chat_id) != str(allowed_id):
        await context.bot.send_message(chat_id=chat_id, text="⛔ **Unauthorized.**\nThis bot is not configured for your user ID.")
        return

    await context.bot.send_message(chat_id=chat_id, text="🚀 **Starting Scraper...**\nRunning in background with `--resume`...")
    
    try:
        # Run in a separate process so it doesn't block the bot
        # Using creationflags=subprocess.CREATE_NEW_CONSOLE to open a new window (Windows specific)
        # remove creationflags if not on Windows or if you want it hidden
        subprocess.Popen(["python", "image_scraper.py", "--resume"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        await context.bot.send_message(chat_id=chat_id, text="✅ Process launched! Check the server console.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to start process: {str(e)}")

async def stop_scraper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /stop command.
    """
    chat_id = update.effective_chat.id
    # Authorization check...
    
    await context.bot.send_message(chat_id=chat_id, text="⚠️ **Stop Command**\nFunctionality to kill specific process is experimental. Please close the console window manually for now.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Shopify Scraper Bot Commands**

/start - Register your user and check status.
/run - Start the Scraper (Resuming mode).
/status - Check if scraper is running (Coming Soon).
/stop - Stop the scraper (Coming Soon).
    """
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text, parse_mode='Markdown')

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('run', run_scraper))
    application.add_handler(CommandHandler('stop', stop_scraper))
    application.add_handler(CommandHandler('help', help_command))
    
    print("🤖 Bot Server Started. Press Ctrl+C to stop.")
    application.run_polling()
