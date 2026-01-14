"""
Telegram → Claude CLI Bridge

Smart bridge that:
1. Forwards Telegram messages to Claude CLI
2. Monitors Claude output and alerts only when decision needed
3. Provides webtmux URL via Cloudflare tunnel
"""
import os
import subprocess
import asyncio
import logging
import re
import signal
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMUX_PANE = "%0"
POLL_INTERVAL = 3  # seconds
last_output_hash = ""
user_chat_id = None
tunnel_process = None
tunnel_url = None

# Detection patterns
DECISION_PATTERNS = [
    r"Enter to select", r"\[y/N\]", r"\[Y/n\]", r"yes/no",
    r"Press .* to continue", r"❯.*\n.*\n.*\n.*1\.",
    r"Do you want to", r"Would you like to", r"승인|거부|선택",
]
COMPLETION_PATTERNS = [r"✓.*완료", r"Successfully", r"Done!", r"Created.*file", r"PR.*created"]
ERROR_PATTERNS = [r"Error:", r"Failed:", r"❌", r"에러", r"실패"]


def start_tunnel():
    """Start Cloudflare tunnel for webtmux."""
    global tunnel_process, tunnel_url
    try:
        # Kill existing tunnel
        if tunnel_process:
            tunnel_process.terminate()
        
        # Start new tunnel
        tunnel_process = subprocess.Popen(
            [os.path.expanduser("~/.local/bin/cloudflared"), "tunnel", "--url", "http://localhost:8080"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        
        # Wait for URL
        for _ in range(30):  # 30 second timeout
            line = tunnel_process.stdout.readline()
            if "trycloudflare.com" in line:
                # Extract URL
                match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
                if match:
                    tunnel_url = match.group(0)
                    return tunnel_url
        return None
    except Exception as e:
        logger.error(f"Tunnel error: {e}")
        return None


def stop_tunnel():
    """Stop Cloudflare tunnel."""
    global tunnel_process, tunnel_url
    if tunnel_process:
        tunnel_process.terminate()
        tunnel_process = None
    tunnel_url = None


def send_to_tmux(text: str) -> str:
    try:
        subprocess.run(["tmux", "send-keys", "-t", TMUX_PANE, "-l", text], check=True)
        subprocess.run(["tmux", "send-keys", "-t", TMUX_PANE, "C-m"], check=True)
        return "✅ Sent"
    except Exception as e:
        return f"❌ Error: {e}"


def read_tmux_output(lines: int = 50) -> str:
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", TMUX_PANE, "-p", "-S", f"-{lines}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return ""


def detect_needs_attention(output: str) -> tuple[bool, str, str]:
    for pattern in DECISION_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE | re.MULTILINE):
            lines = output.split('\n')[-30:]
            return True, "decision", '\n'.join(lines)
    for pattern in COMPLETION_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            return True, "complete", '\n'.join(output.split('\n')[-10:])
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, output):
            return True, "error", '\n'.join(output.split('\n')[-15:])
    return False, "", ""


async def poll_claude(app):
    global last_output_hash, user_chat_id
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        if not user_chat_id:
            continue
        
        output = read_tmux_output(60)
        output_hash = hash(output[-500:] if len(output) > 500 else output)
        if output_hash == last_output_hash:
            continue
        last_output_hash = output_hash
        
        needs_attention, alert_type, message = detect_needs_attention(output)
        if needs_attention:
            headers = {"decision": "🔔 *선택 필요*", "complete": "✅ *완료*", "error": "❌ *에러*"}
            header = headers.get(alert_type, "📢 *알림*")
            if len(message) > 3000:
                message = message[-3000:]
            try:
                await app.bot.send_message(chat_id=user_chat_id, text=f"{header}\n\n```\n{message}\n```", parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Alert error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id, tunnel_url
    user_chat_id = update.effective_chat.id
    
    await update.message.reply_text("🚀 Starting Cloudflare tunnel...")
    
    # Start tunnel in background
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(None, start_tunnel)
    
    if url:
        await update.message.reply_text(
            f"🤖 *Claude CLI Bridge*\n\n"
            f"🌐 *webtmux*: {url}\n"
            f"🔑 ID: `admin` / PW: `admin123`\n\n"
            f"*Commands:*\n"
            f"/status - Claude 화면\n"
            f"/stop - 종료\n\n"
            f"메시지 → Claude 전달\n"
            f"숫자 (1,2,3) → 선택",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🤖 *Claude CLI Bridge* (tunnel failed)\n\n"
            "/status - Claude 화면\n/stop - 종료",
            parse_mode="Markdown"
        )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = read_tmux_output(60)
    if len(output) > 4000:
        output = output[-4000:]
    await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = send_to_tmux("/clear")
    await update.message.reply_text(result)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop all services."""
    stop_tunnel()
    await update.message.reply_text("🛑 Tunnel stopped.\n\nTo fully exit, Ctrl+C the bot process.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id
    user_chat_id = update.effective_chat.id
    text = update.message.text
    result = send_to_tmux(text)
    await update.message.reply_text(result)


async def post_init(app):
    asyncio.create_task(poll_claude(app))


def main():
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
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Starting Telegram bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
