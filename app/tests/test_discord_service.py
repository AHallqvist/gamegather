import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from src.services.discord_service import DiscordService, connect_command


class DiscordServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_dms_id_and_confirms_privately(self) -> None:
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=123456, send=AsyncMock()),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await connect_command(interaction)
        self.assertIn("123456", interaction.user.send.call_args.args[0])
        interaction.followup.send.assert_awaited_once_with(
            "Check your DMs for your user ID.", ephemeral=True,
        )

    async def test_connect_reports_blocked_dms_privately(self) -> None:
        response = SimpleNamespace(status=403, reason="Forbidden")
        interaction = SimpleNamespace(
            user=SimpleNamespace(send=AsyncMock(side_effect=discord.Forbidden(response, "blocked")), id=123),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await connect_command(interaction)
        self.assertIn("couldn't DM", interaction.followup.send.call_args.args[0])
        self.assertTrue(interaction.followup.send.call_args.kwargs["ephemeral"])

    async def test_worker_bridge_sends_without_blocking_event_loop(self) -> None:
        service = DiscordService(1554629817159393291)
        user = SimpleNamespace(send=AsyncMock())
        service.client.is_ready = MagicMock(return_value=True)
        service.client.fetch_user = AsyncMock(return_value=user)
        await asyncio.to_thread(service.send_from_worker, "123456", "Attendance: https://example.com/attendance/token")
        service.client.fetch_user.assert_awaited_once_with(123456)
        self.assertIn("/attendance/token", user.send.call_args.args[0])
        await service.close()

    async def test_forbidden_delivery_is_permanent(self) -> None:
        service = DiscordService(1554629817159393291)
        response = SimpleNamespace(status=403, reason="Forbidden")
        service.client.is_ready = MagicMock(return_value=True)
        service.client.fetch_user = AsyncMock(side_effect=discord.Forbidden(response, "blocked"))
        with self.assertRaisesRegex(ValueError, "cannot DM"):
            await service.send_dm("123456", "Test")
        await service.close()

    async def test_invalid_id_does_not_contact_discord(self) -> None:
        service = DiscordService(1554629817159393291)
        service.client.fetch_user = AsyncMock()
        with self.assertRaisesRegex(ValueError, "numeric user ID"):
            await service.send_dm("not-an-id", "Test")
        service.client.fetch_user.assert_not_awaited()
        await service.close()

    async def test_guild_command_needs_no_privileged_intents(self) -> None:
        service = DiscordService(1554629817159393291)
        commands = service.client.tree.get_commands(guild=service.client.guild)
        self.assertEqual([command.name for command in commands], ["connect"])
        self.assertFalse(service.client.intents.message_content)
        self.assertFalse(service.client.intents.members)
        await service.close()

    async def test_invalid_token_fails_bot_startup(self) -> None:
        service = DiscordService(1554629817159393291)
        with patch.object(service.client, "start", AsyncMock(side_effect=discord.LoginFailure("Invalid token"))):
            with self.assertRaises(discord.LoginFailure):
                await service.start("placeholder")
        self.assertTrue(service.client.is_closed())
