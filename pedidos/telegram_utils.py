import urllib.request
import urllib.parse
import json
import threading
from django.conf import settings
from django.core.signing import TimestampSigner

def generate_action_token(order_id, action):
    signer = TimestampSigner()
    # Sign format: "order_id:action"
    return signer.sign(f"{order_id}:{action}")

def send_telegram_message(message, buttons=None):
    """
    Sends a message to the configured Telegram chat.
    Supports optional inline keyboard buttons.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        return

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    if buttons:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": buttons
        })

    def _send():
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = json.dumps(payload).encode("utf-8")
            
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req) as response:
                pass 
        except Exception as e:
            print(f"Error sending Telegram: {e}")

    thread = threading.Thread(target=_send)
    thread.start()
