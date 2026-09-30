import os
import unittest
from unittest.mock import patch

from src.services.notification_methods import (
    enabled_methods,
    require_enabled_method,
    validate_notification_configuration,
)


class NotificationConfigurationTests(unittest.TestCase):
    def test_no_enabled_method_fails(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "No notification methods enabled"):
                validate_notification_configuration()

    def test_invalid_flag_does_not_log_its_value(self) -> None:
        with patch.dict(os.environ, {"EMAIL_ENABLED": "invalid-flag-value"}, clear=True):
            with self.assertLogs("src.services.notification_methods", level="ERROR") as logs:
                with self.assertRaisesRegex(ValueError, "EMAIL_ENABLED must be true or false"):
                    validate_notification_configuration()
            self.assertNotIn("invalid-flag-value", " ".join(logs.output))

    def test_missing_variables_logged_without_present_values(self) -> None:
        environment = {"EMAIL_ENABLED": "true", "MAILJET_SMTP_PASSWORD": "private-value"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertLogs("src.services.notification_methods", level="ERROR") as logs:
                with self.assertRaisesRegex(ValueError, "MAILJET_SMTP_USERNAME"):
                    validate_notification_configuration()
            output = " ".join(logs.output)
            self.assertNotIn("private-value", output)
            self.assertNotIn("MAILJET_SMTP_PASSWORD", output)

    def test_present_empty_and_placeholder_values_pass_startup(self) -> None:
        environment = {
            "EMAIL_ENABLED": "true", "MAILJET_SMTP_HOST": "",
            "MAILJET_SMTP_PORT": "not-a-port", "MAILJET_SMTP_USERNAME": "replace-with-key",
            "MAILJET_SMTP_PASSWORD": "", "MAIL_FROM_ADDRESS": "",
        }
        with patch.dict(os.environ, environment, clear=True):
            validate_notification_configuration()
            self.assertEqual([method.name for method in enabled_methods()], ["email"])

    def test_disabled_method_is_rejected(self) -> None:
        with patch.dict(os.environ, {"EMAIL_ENABLED": "false"}, clear=True):
            with self.assertRaisesRegex(ValueError, "not enabled"):
                require_enabled_method("email")

    def test_discord_requires_guild_id(self) -> None:
        environment = {"DISCORD_ENABLED": "true", "DISCORD_BOT_TOKEN": "placeholder"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ValueError, "DISCORD_GUILD_ID"):
                validate_notification_configuration()

    def test_discord_only_deployment_passes_configuration(self) -> None:
        environment = {
            "DISCORD_ENABLED": "true", "DISCORD_BOT_TOKEN": "placeholder",
            "DISCORD_GUILD_ID": "1554629817159393291",
        }
        with patch.dict(os.environ, environment, clear=True):
            validate_notification_configuration()
            self.assertEqual([method.name for method in enabled_methods()], ["discord"])


if __name__ == "__main__":
    unittest.main()
