import os
import requests
from core.logging_config import add_log
from core.redis_client import get_redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_frontend_url():
    """Retrieve frontend URL from Redis config."""
    r = get_redis()
    if r:
        url = r.get("config:frontend_url")
        if url:
            return url.decode('utf-8') if isinstance(url, bytes) else url
    return None

def send_telegram_notification(chat_id: str, message: str, dashboard_link: bool = True):
    """
    Send a notification to a Telegram chat.
    
    Args:
        chat_id: Telegram Chat ID
        message: Message text (supports HTML)
        dashboard_link: Whether to append a link to the dashboard
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        add_log("TELEGRAM", "Skipping notification: TELEGRAM_BOT_TOKEN not set", "warning")
        return
        
    if not chat_id:
        chat_id = "7508230549"
        add_log("TELEGRAM", f"Using default chat_id: {chat_id}", "info")
        
    text = message
    
    if dashboard_link:
        fe_url = get_frontend_url()
        if fe_url:
            text += f"\n\n👉 <a href='{fe_url}?tab=pending'>대시보드에서 확인하기</a>"
        else:
            text += "\n\n(대시보드 URL을 찾을 수 없습니다)"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        add_log("TELEGRAM", f"Sent notification to {chat_id}", "success")
    except Exception as e:
        add_log("TELEGRAM", f"Failed to send notification: {str(e)}", "failed")
