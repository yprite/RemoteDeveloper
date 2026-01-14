"""
Telegram → Claude CLI Bridge

Smart bridge that:
1. Forwards Telegram messages to Claude CLI
2. Monitors Claude output and alerts only when decision needed
"""
import os
import subprocess
import asyncio
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMUX_PANE = "%0"
POLL_INTERVAL = 3  # seconds
last_output_hash = ""
user_chat_id = None  # Store user's chat ID for proactive alerts


# Detection patterns for when user input is needed
DECISION_PATTERNS = [
    r"Enter to select",          # Choice menu
    r"\[y/N\]",                   # Yes/No prompt
    r"\[Y/n\]",                   # Yes/No prompt
    r"yes/no",                    # Confirmation
    r"Press .* to continue",     # Wait for key
    r"❯.*\n.*\n.*\n.*1\.",       # Numbered choices
    r"Do you want to",           # Question
    r"Would you like to",        # Question
    r"승인|거부|선택",             # Korean approval
]

COMPLETION_PATTERNS = [
    r"✓.*완료",
    r"Successfully",
    r"Done!",
    r"Created.*file",
    r"PR.*created",
]

ERROR_PATTERNS = [
    r"Error:",
    r"Failed:",
    r"❌",
    r"에러",
    r"실패",
]


def send_to_tmux(text: str) -> str:
    """Send text to Claude CLI in tmux."""
    try:
        subprocess.run(["tmux", "send-keys", "-t", TMUX_PANE, "-l", text], check=True)
        subprocess.run(["tmux", "send-keys", "-t", TMUX_PANE, "C-m"], check=True)
        return "✅ Sent to Claude"
    except Exception as e:
        return f"❌ Error: {e}"


def read_tmux_output(lines: int = 50) -> str:
    """Read recent output from tmux pane."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_PANE, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error reading: {e}"


def detect_needs_attention(output: str) -> tuple[bool, str, str]:
    """Check if output needs user attention. Returns (needs_attention, type, message)."""
    # Check for decision needed
    for pattern in DECISION_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
            # Extract relevant part (last 30 lines)
            lines = output.split('\n')[-30:]
            return True, "decision", '\n'.join(lines)
    
    # Check for completion
    for pattern in COMPLETION_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            lines = output.split('\n')[-10:]
            return True, "complete", '\n'.join(lines)
    
    # Check for errors
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, output):
            lines = output.split('\n')[-15:]
            return True, "error", '\n'.join(lines)
    
    return False, "", ""


async def poll_claude(app):
    """Periodically check Claude output for attention-needed events."""
    global last_output_hash, user_chat_id
    
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        
        if not user_chat_id:
            continue
        
        output = read_tmux_output(60)
        output_hash = hash(output[-500:] if len(output) > 500 else output)
        
        # Skip if output hasn't changed
        if output_hash == last_output_hash:
            continue
        last_output_hash = output_hash
        
        # Check if attention needed
        needs_attention, alert_type, message = detect_needs_attention(output)
        
        if needs_attention:
            # Format message based on type
            if alert_type == "decision":
                header = "🔔 *선택이 필요합니다*"
            elif alert_type == "complete":
                header = "✅ *작업 완료*"
            elif alert_type == "error":
                header = "❌ *에러 발생*"
            else:
                header = "📢 *알림*"
            
            # Truncate if too long
            if len(message) > 3000:
                message = message[-3000:]
            
            try:
                await app.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"{header}\n\n```\n{message}\n```",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    global user_chat_id
    user_chat_id = update.effective_chat.id
    await update.message.reply_text(
        "🤖 *Claude CLI Bridge*\n\n"
        "*Commands:*\n"
        "/status - Claude 화면 보기\n"
        "/clear - 새 대화\n\n"
        "메시지 → Claude 전달\n"
        "숫자 (1,2,3) → 선택지 선택\n\n"
        "✨ *스마트 알림:* 선택/에러/완료 시 자동 알림",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent Claude output."""
    output = read_tmux_output(60)
    if len(output) > 4000:
        output = output[-4000:]
    await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send /clear to start new conversation."""
    result = send_to_tmux("/clear")
    await update.message.reply_text(result)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward message to Claude CLI."""
    global user_chat_id
    user_chat_id = update.effective_chat.id
    
    text = update.message.text
    result = send_to_tmux(text)
    await update.message.reply_text(result)


async def post_init(app):
    """Start polling after bot initialization."""
    asyncio.create_task(poll_claude(app))


def main():
    """Start the bot."""
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found")
        return
    
    app = Application.builder().token(token).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Starting Telegram bot with smart polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
