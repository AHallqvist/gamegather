"""Deployment configuration shared by notification forms and delivery."""

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable


logger = logging.getLogger(__name__)


def send_email_notification(item: Any) -> None:
    from src.services.notification_service import _send_email, _smtp_settings

    _send_email(item, _smtp_settings())


def send_discord_notification(item: Any) -> None:
    from src.services.discord_service import send_discord_notification as send

    send(item)


def send_sms_notification(item: Any) -> None:
    from src.services.sms_service import send_sms_notification as send

    send(item)


def send_telegram_notification(item: Any) -> None:
    from src.services.telegram_service import send_telegram_notification as send

    send(item)


@dataclass(frozen=True)
class NotificationMethod:
    name: str
    label: str
    flag: str
    required_variables: tuple[str, ...]
    target_label: str
    instructions: str
    sender: Callable[[Any], None] | None


METHODS = {
    "email": NotificationMethod(
        name="email",
        label="Email",
        flag="EMAIL_ENABLED",
        required_variables=(
            "MAILJET_SMTP_HOST", "MAILJET_SMTP_PORT", "MAILJET_SMTP_USERNAME",
            "MAILJET_SMTP_PASSWORD", "MAIL_FROM_ADDRESS",
        ),
        target_label="Email address",
        instructions="Enter the email address where you want to receive notifications.",
        sender=send_email_notification,
    ),
    "discord": NotificationMethod(
        name="discord",
        label="Discord",
        flag="DISCORD_ENABLED",
        required_variables=("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID"),
        target_label="Discord user ID",
        instructions="Join the GameGather Discord server and run /connect. "
                     "The bot DMs you your user ID; paste it here.",
        sender=send_discord_notification,
    ),
    "sms": NotificationMethod(
        name="sms", label="SMS", flag="SMS_ENABLED",
        required_variables=("VONAGE_API_KEY", "VONAGE_API_SECRET", "VONAGE_SMS_FROM"),
        target_label="Swedish mobile number",
        instructions="SMS is available only for Swedish mobile numbers (+46). "
                     "Use +46 and omit the leading 0: 0701234567 becomes +46701234567. "
                     "For other numbers, choose email or Discord if available.",
        sender=send_sms_notification,
    ),
    "telegram": NotificationMethod(
        name="telegram", label="Telegram", flag="TELEGRAM_ENABLED",
        required_variables=("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_USERNAME"),
        target_label="Telegram private chat ID",
        instructions="Open the GameGather Telegram bot and press Start. "
                     "Copy the private chat ID from its reply and paste it here.",
        sender=send_telegram_notification,
    ),
}


def _enabled(method: NotificationMethod) -> bool:
    value = os.environ.get(method.flag, "false").strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{method.flag} must be true or false")
    return value == "true"


def enabled_methods() -> list[NotificationMethod]:
    return [method for method in METHODS.values() if _enabled(method)]


def require_enabled_method(name: str) -> NotificationMethod:
    method = METHODS.get(name)
    if method is None or not _enabled(method) or method.sender is None:
        raise ValueError("Notification method is not enabled")
    return method


def validate_notification_target(name: str, target: str) -> str:
    require_enabled_method(name)
    if name == "sms":
        from src.services.sms_service import validate_swedish_mobile

        return validate_swedish_mobile(target)
    if name == "telegram":
        from src.services.telegram_service import validate_chat_id

        return validate_chat_id(target)
    return target


def validate_notification_configuration() -> None:
    """Fail startup on absent variables, never logging their values."""
    try:
        methods = enabled_methods()
        if not methods:
            raise ValueError("No notification methods enabled. Enable at least one provider.")
        missing = [
            variable for method in methods for variable in method.required_variables
            if variable not in os.environ
        ]
        if missing:
            raise ValueError("Missing notification environment variables: " + ", ".join(missing))
        for method in methods:
            if method.sender is None:
                raise ValueError(f"Notification provider is not implemented: {method.name}")
    except ValueError as exc:
        logger.error("%s", exc)
        raise


def send_notification(item: Any) -> None:
    method = require_enabled_method(item["notification_method"])
    method.sender(item)
