import os
import logging
import subprocess
import json
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Import libraries
try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
    from google import genai
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Please run: pip install python-telegram-bot google-genai")
    exit(1)

# Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
# specific model ID verified to work
MODEL_ID = "gemini-2.5-flash"

# Conversation history (simple in-memory storage)
conversation_history = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command."""
    chat_id = update.effective_chat.id
    
    if str(chat_id) != str(CHAT_ID):
        await context.bot.send_message(chat_id=chat_id, text="⛔ Unauthorized.")
        return
    
    msg = """🤖 **AI-Powered Shopify Bot**

I'm connected to Google Gemini and can help you with:
- Editing code files
- Running commands
- Debugging issues
- Answering questions about your project

Just send me a message like you would chat with an AI assistant!

**Commands:**
/start - This message
/clear - Clear conversation history
/status - Check bot status
"""
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history."""
    global conversation_history
    conversation_history = []
    await update.message.reply_text("✅ Conversation history cleared.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status."""
    msg = f"""📊 **Bot Status**

✅ Telegram: Connected
✅ Gemini API: Connected
📝 Conversation History: {len(conversation_history)} messages
📁 Working Directory: `{os.getcwd()}`
"""
    await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and forward to Gemini."""
    chat_id = update.effective_chat.id
    
    # Authorization check
    if str(chat_id) != str(CHAT_ID):
        await context.bot.send_message(chat_id=chat_id, text="⛔ Unauthorized.")
        return
    
    user_message = update.message.text
    
    # Send "thinking" indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Build system instruction
    system_instruction = f"""You are an AI assistant helping a user manage their Shopify scraping project via Telegram.

Working Directory: {os.getcwd()}
Project: Shopify Image Scraper (Python)

Key Files:
- image_scraper.py: Main scraper script
- bot_server.py: Telegram bot (basic version)
- ai_bot_server.py: This AI-powered bot
- .env: Environment variables

When the user asks you to:
1. **Edit files**: Respond with a JSON action in this format:
   ```json
   {{"action": "edit_file", "file": "path/to/file.py", "description": "what you're doing", "content": "new file content or diff"}}
   ```

2. **Run commands**: Respond with:
   ```json
   {{"action": "run_command", "command": "python image_scraper.py --resume", "description": "Running scraper"}}
   ```

3. **Answer questions**: Just respond normally with text.

IMPORTANT: 
- Always explain what you're doing BEFORE the JSON action.
- Keep responses concise for Telegram (max 4096 chars).
- If you need to edit a file, provide the FULL file content or clear instructions.
"""
    
    # Add to conversation history
    conversation_history.append({"role": "user", "parts": [user_message]})
    
    try:
        # Call Gemini API with new client and system instruction
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=user_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        ai_response = response.text
        
        # Add AI response to history
        conversation_history.append({"role": "model", "parts": [ai_response]})
        
        # Send AI response to Telegram
        await send_long_message(context, chat_id, ai_response)
        
        # Check if response contains actions
        if "```json" in ai_response:
            # Extract JSON blocks
            import re
            json_blocks = re.findall(r'```json\n(.*?)\n```', ai_response, re.DOTALL)
            
            for json_str in json_blocks:
                try:
                    action = json.loads(json_str)
                    await execute_action(context, chat_id, action)
                except json.JSONDecodeError:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ Failed to parse action JSON.")
        
    except Exception as e:
        error_msg = f"❌ **Error:**\n```\n{str(e)}\n```"
        await context.bot.send_message(chat_id=chat_id, text=error_msg, parse_mode='Markdown')

async def send_long_message(context, chat_id, text, parse_mode='Markdown'):
    """Send long messages by splitting them if needed."""
    max_length = 4096
    
    if len(text) <= max_length:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        except:
            # Fallback without markdown if parsing fails
            await context.bot.send_message(chat_id=chat_id, text=text)
    else:
        # Split into chunks
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for chunk in chunks:
            try:
                await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode)
            except:
                await context.bot.send_message(chat_id=chat_id, text=chunk)

async def execute_action(context, chat_id, action):
    """Execute actions requested by the AI."""
    action_type = action.get("action")
    
    if action_type == "run_command":
        cmd = action.get("command")
        desc = action.get("description", "Running command")
        
        await context.bot.send_message(chat_id=chat_id, text=f"⚙️ {desc}\n```\n{cmd}\n```", parse_mode='Markdown')
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            output = result.stdout if result.stdout else result.stderr
            output = output[:3000] if output else "No output"
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **Command Output:**\n```\n{output}\n```",
                parse_mode='Markdown'
            )
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Command failed: {str(e)}")
    
    elif action_type == "edit_file":
        file_path = action.get("file")
        content = action.get("content")
        desc = action.get("description", "Editing file")
        
        await context.bot.send_message(chat_id=chat_id, text=f"📝 {desc}\nFile: `{file_path}`", parse_mode='Markdown')
        
        try:
            # Create backup
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                with open(file_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            await context.bot.send_message(chat_id=chat_id, text=f"✅ File updated: `{file_path}`", parse_mode='Markdown')
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ File edit failed: {str(e)}")

if __name__ == '__main__':
    if not TOKEN or not GEMINI_API_KEY:
        print("Error: TELEGRAM_BOT_TOKEN and GEMINI_API_KEY must be set in .env")
        exit(1)
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('clear', clear_history))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 AI Bot Server Started. Send messages to your bot on Telegram!")
    application.run_polling()
