import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime


STEAM_PRICE_URL = "https://steamcommunity.com/market/priceoverview/"
TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"

DEFAULT_INTERVAL_SECONDS = 600
DEFAULT_APP_ID = "730"
DEFAULT_CURRENCY = "1"
DEFAULT_MARKET_HASH_NAME = "Gallery Case"
DEFAULT_CHAT_ID = "@gallerystrategy_price"


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


def request_json(url, params=None, timeout=20):
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset))


def get_steam_price(app_id, currency, market_hash_name):
    data = request_json(
        STEAM_PRICE_URL,
        {
            "appid": app_id,
            "currency": currency,
            "market_hash_name": market_hash_name,
        },
    )

    if not data.get("success"):
        raise RuntimeError(f"Steam returned unsuccessful response: {data}")

    price = data.get("lowest_price") or data.get("median_price")
    if not price:
        raise RuntimeError(f"Steam response has no price: {data}")

    return price


def send_telegram_message(token, chat_id, text):
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        TELEGRAM_SEND_URL.format(token=token),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        data = json.loads(response.read().decode(charset))

    if not data.get("ok"):
        raise RuntimeError(f"Telegram returned error: {data}")


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main():
    load_env_file()

    token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID)
    app_id = os.environ.get("STEAM_APP_ID", DEFAULT_APP_ID)
    currency = os.environ.get("STEAM_CURRENCY", DEFAULT_CURRENCY)
    market_hash_name = os.environ.get("STEAM_MARKET_HASH_NAME", DEFAULT_MARKET_HASH_NAME)
    interval_seconds = int(os.environ.get("INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))

    log(f"Started. Posting {market_hash_name} price to {chat_id} every {interval_seconds} seconds.")

    while True:
        try:
            price = get_steam_price(app_id, currency, market_hash_name)
            send_telegram_message(token, chat_id, price)
            log(f"Published price: {price}")
        except Exception as error:
            log(f"Error: {error}")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped.")
    except Exception as error:
        log(f"Fatal error: {error}")
        sys.exit(1)
