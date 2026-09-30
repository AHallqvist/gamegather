# GameGather

A Python-first MVP for organizing pick-up games with an initial focus on BOTC-style gatherings.

## Quick start

1. Copy `.env.example` to `.env` and adjust values.
2. Build and run:

```bash
docker compose up --build
```

3. Open http://localhost:3000

## Discord notifications

Set `DISCORD_ENABLED=true`, `DISCORD_BOT_TOKEN`, and `DISCORD_GUILD_ID` in your
local `.env` using the names documented in `.env.example`. Set `BASE_URL` to the
address players can reach; it is used in organizer and attendance links.

Invite the bot to the configured server with the `bot` and `applications.commands`
scopes. Privileged intents (including Message Content) are not needed. The app
connects the bot and registers `/connect` in that server during startup.

Players and organizers can run `/connect` in the server to receive their Discord
user ID by DM, then select Discord and paste that ID into the website form.
If DMs are blocked, the command explains how to enable them. Verification is
optional and no user accounts or linking records are stored.

The notification queue sends confirmations, minimum-player alerts, and gathering
requests by DM when Discord is selected. Unknown users and blocked DMs are marked
as failed; temporary delivery errors use the queue's retry policy. Email remains
available when `EMAIL_ENABLED=true`.

## SMS notifications

Enable `SMS_ENABLED=true` and set `VONAGE_API_KEY`, `VONAGE_API_SECRET`, and
`VONAGE_SMS_FROM` using `.env.example`. The sender defaults in the example to
`GameGather`. Rebuild the container to install the phone-number validation library.

SMS is available only for Swedish mobile numbers in international format, for
example `+46701234567` (omit the leading zero from `0701234567`). Both forms show
format instructions and inline validation; API submissions are validated too.
Norwegian numbers, Swedish landlines, and local-format numbers are rejected.

Messages contain a short game description and the private organizer or attendance
link. `sent` means Vonage accepted the message, not confirmed handset delivery.
Vonage charges per SMS segment; long links and Unicode can require extra segments.

## Telegram notifications

Set `TELEGRAM_ENABLED=true`, `TELEGRAM_BOT_TOKEN`, and
`TELEGRAM_BOT_USERNAME=gamegather_notifications_bot` using `.env.example`.
Open https://t.me/gamegather_notifications_bot and press Start. The bot replies
in the private chat with the chat ID to enter when selecting Telegram on the
website. No user accounts or verification records are stored.

The app uses long polling, so no public webhook endpoint is needed. Run one
polling app instance per bot token, and do not configure a webhook for this bot.
Telegram sends organizer confirmations, minimum-player alerts, and private
attendance links through the existing queue and retry policy. Set `BASE_URL`
to an address recipients can reach.

## Purpose

This project implements the first slice of the product described in `design.md`:

- create a game proposal
- track player interest
- reach a minimum threshold
- start gathering
- accept attendance responses

## Stack

- Python
- FastAPI
- SQLite
- Docker Compose

This keeps the core game logic readable and easy to reason about while still supporting portable deployment.
