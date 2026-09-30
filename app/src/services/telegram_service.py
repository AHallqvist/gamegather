"""Telegram private chat setup and notification delivery, without user accounts."""

import asyncio
import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


def _raise_api_error(code: int) -> None:
    # Do not include response descriptions or request URLs: URLs contain the token.
    if code == 429 or code >= 500:
        raise RuntimeError(f"Telegram temporary API error (HTTP {code})") from None
    raise ValueError(f"Telegram rejected request (HTTP {code})") from None


def telegram_request(method: str, payload: dict[str, Any]) -> Any:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read())
    except HTTPError as exc:
        _raise_api_error(exc.code)
    except (URLError, OSError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Telegram connection or response error") from None
    if not isinstance(result, dict):
        raise RuntimeError("Telegram returned an unexpected response")
    if result.get("ok") is not True:
        code = result.get("error_code", 500)
        _raise_api_error(code if isinstance(code, int) else 500)
    return result.get("result")


def validate_chat_id(target: str) -> str:
    """Accept a private numeric chat ID, never a group ID or username."""
    if not target.isascii() or not target.isdecimal() or not 0 < int(target) < 2**52:
        raise ValueError("Enter the positive Telegram chat ID received from the bot.")
    return target


def send_message(target: str, text: str) -> None:
    validate_chat_id(target)
    for offset in range(0, len(text), 4000):
        telegram_request("sendMessage", {
            "chat_id": target,
            "text": text[offset:offset + 4000],
            "link_preview_options": {"is_disabled": True},
        })


def send_telegram_notification(item: Any) -> None:
    from src.services.notification_service import notification_content

    subject, body = notification_content(item)
    send_message(str(item["notification_target"]), f"{subject}\n\n{body}")


def handle_update(update: dict[str, Any]) -> None:
    message = update.get("message", {})
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return
    command = str(message.get("text", "")).split()
    if not command or command[0].split("@")[0] != "/start":
        return
    chat_id = str(chat["id"])
    send_message(
        chat_id,
        "You can receive GameGather messages!\n\n"
        f"Your Telegram private chat ID: {chat_id}\n\n"
        "Choose Telegram when creating a game or registering and paste this ID "
        "into the notification address or ID field.",
    )


class TelegramService:
    def __init__(self) -> None:
        self.stop = asyncio.Event()
        self.task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        await asyncio.to_thread(telegram_request, "getMe", {})
        webhook = await asyncio.to_thread(telegram_request, "getWebhookInfo", {})
        if not isinstance(webhook, dict):
            raise RuntimeError("Telegram returned unexpected webhook information")
        if webhook.get("url"):
            raise ValueError("Telegram bot has a webhook configured; remove it to use long polling")
        self.task = asyncio.create_task(self.poll())
        logger.info("GameGather Telegram bot connected")

    async def poll(self) -> None:
        offset = 0
        while not self.stop.is_set():
            try:
                updates = await asyncio.to_thread(telegram_request, "getUpdates", {
                    "offset": offset, "timeout": 5, "limit": 20,
                    "allowed_updates": ["message"],
                })
                if not isinstance(updates, list):
                    raise RuntimeError("Telegram returned unexpected updates")
                for update in updates:
                    if self.stop.is_set():
                        break
                    try:
                        await asyncio.to_thread(handle_update, update)
                    except (RuntimeError, ValueError) as exc:
                        logger.warning("Telegram /start reply failed: %s", exc)
                    offset = update["update_id"] + 1
            except (RuntimeError, ValueError) as exc:
                logger.warning("Telegram polling failed: %s", exc)
                try:
                    await asyncio.wait_for(self.stop.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass

    async def close(self) -> None:
        self.stop.set()
        if self.task is not None:
            # Let the bounded HTTP poll finish rather than abandon its worker thread.
            await self.task
