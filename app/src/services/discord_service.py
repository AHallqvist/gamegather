"""Discord bot connection, opt-in DM check, and notification delivery."""

import asyncio
import logging
import os
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

import discord
from discord import app_commands


logger = logging.getLogger(__name__)
_service: "DiscordService | None" = None


async def connect_command(interaction: discord.Interaction) -> None:
    """DM the caller their ID; no identity or verification record is stored."""
    await interaction.response.defer(ephemeral=True)
    try:
        await interaction.user.send(
            "You can receive GameGather messages!\n\n"
            f"Your Discord user ID: {interaction.user.id}\n\n"
            "Choose Discord when creating a game or registering, and paste this ID "
            "into the notification address or ID field.",
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I couldn't DM you. Allow direct messages from members of this server "
            "and check that the bot isn't blocked, then try /connect again. "
            "You can also choose email if it is available.",
            ephemeral=True,
        )
    except discord.HTTPException:
        await interaction.followup.send(
            "Discord couldn't deliver the DM just now. Please try /connect again later.",
            ephemeral=True,
        )
    else:
        await interaction.followup.send("Check your DMs for your user ID.", ephemeral=True)


class GameGatherClient(discord.Client):
    def __init__(self, guild_id: int) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.guild = discord.Object(id=guild_id)
        self.tree = app_commands.CommandTree(self)
        self.tree.add_command(
            app_commands.Command(
                name="connect",
                description="Check that GameGather can DM you and get your Discord user ID.",
                callback=connect_command,
            ),
            guild=self.guild,
        )
        self.connected = asyncio.Event()

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=self.guild)

    async def on_ready(self) -> None:
        self.connected.set()
        logger.info("GameGather Discord bot connected")


class DiscordService:
    def __init__(self, guild_id: int) -> None:
        self.client = GameGatherClient(guild_id)
        self.loop = asyncio.get_running_loop()
        self.task: asyncio.Task[None] | None = None

    async def start(self, token: str) -> None:
        self.task = asyncio.create_task(self.client.start(token))
        ready = asyncio.create_task(self.client.connected.wait())
        try:
            done, _ = await asyncio.wait(
                (self.task, ready), timeout=60, return_when=asyncio.FIRST_COMPLETED,
            )
            if self.task in done:
                await self.task
                raise RuntimeError("Discord bot disconnected during startup")
            if ready not in done:
                raise TimeoutError("Discord bot did not become ready within 60 seconds")
        except BaseException:
            await self.close()
            raise
        finally:
            ready.cancel()
            await asyncio.gather(ready, return_exceptions=True)

    async def close(self) -> None:
        await self.client.close()
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def send_dm(self, target: str, content: str) -> None:
        if not target.isascii() or not target.isdecimal() or not 0 < int(target) < 2**64:
            raise ValueError("Discord notification target must be a numeric user ID")
        if not self.client.is_ready():
            raise RuntimeError("Discord bot is not connected")
        try:
            user = await self.client.fetch_user(int(target))
            # Discord messages are limited to 2,000 characters.
            for offset in range(0, len(content), 2000):
                await user.send(
                    content[offset:offset + 2000],
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        except (discord.Forbidden, discord.NotFound) as exc:
            raise ValueError("Discord cannot DM this user (blocked DMs or unknown user)") from exc
        except discord.HTTPException as exc:
            if 400 <= exc.status < 500 and exc.status != 429:
                raise ValueError(f"Discord rejected DM delivery (HTTP {exc.status})") from exc
            raise RuntimeError(f"Discord DM delivery failed (HTTP {exc.status})") from exc

    def send_from_worker(self, target: str, content: str) -> None:
        """Bridge the synchronous queue worker to the bot's async event loop."""
        future = asyncio.run_coroutine_threadsafe(self.send_dm(target, content), self.loop)
        try:
            future.result(timeout=90)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError("Discord DM delivery timed out") from None


async def start_discord_service() -> None:
    global _service
    service = DiscordService(int(os.environ["DISCORD_GUILD_ID"]))
    await service.start(os.environ["DISCORD_BOT_TOKEN"])
    _service = service


async def stop_discord_service() -> None:
    global _service
    if _service is not None:
        await _service.close()
        _service = None


def send_discord_notification(item: Any) -> None:
    from src.services.notification_service import notification_content

    if _service is None:
        raise RuntimeError("Discord bot is not running")
    subject, body = notification_content(item)
    _service.send_from_worker(str(item["notification_target"]), f"{subject}\n\n{body}")
