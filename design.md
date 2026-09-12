# Pick-Up Game Coordinator

## Overview

Pick-Up Game Coordinator is a web application designed to help organize spontaneous and semi-spontaneous social games, with an initial focus on **Blood on the Clocktower (BOTC)**.

The system allows players to express interest in a game, receive notifications when enough players are available, and coordinate gathering with minimal organizer effort.

While BOTC is the primary use case, the design should remain generic enough to support other group activities in the future.

Examples:

- Blood on the Clocktower
- Board games
- RPG one-shots
- Trading card game drafts
- Social deduction games

---

# Goals

## Primary Goals

- Make it easy to propose a game.
- Allow players to register interest quickly.
- Notify players when a game becomes viable.
- Allow organizers to initiate a "gathering phase".
- Collect attendance confirmations.
- Support multiple notification methods.

## Secondary Goals

- Support conventions and gaming events.
- Avoid requiring app installation.
- Minimize organizer workload.
- Be extensible for additional notification channels.

## Non-Goals (Initial Version)

- Running BOTC games.
- Role assignment.
- Script management.
- Scheduling recurring events.
- Social network functionality.

---

# Core Concept

The system is built around the idea that:

> Interest is not the same as commitment.

A player can indicate interest in a game, but the organizer should only attempt to gather players once enough interest has been collected.

The process is intentionally split into multiple stages.

---

# User Roles

## Organizer

Creates game proposals.

Can:

- Create a game
- Edit a game
- Start gathering
- Close a game
- View player status

## Player

Registers interest in games.

Can:

- Join a game
- Leave a game
- Configure notifications
- Confirm attendance during gathering

---

# User Flow

## 1. Create Game Proposal

Organizer creates a proposal.

Example:

```text
Title:
Trouble Brewing

Minimum Players:
8

Ideal Players:
12

Maximum Players:
15

Location:
Table 17

Expected Duration:
2.5 hours
```

The system generates:

- Public URL
- QR Code

---

## 2. Player Registration

Player visits the game page.

They enter:

```text
Display Name
Notification Methods
Optional Notes
```

After registration they receive confirmation.

Example:

```text
You are registered.

Current Players:
7 / 8 minimum
```

---

## 3. Minimum Threshold Reached

When minimum player count is reached:

```text
Minimum players reached.
```

The organizer is notified.

Players may optionally receive:

```text
A game you joined can now be formed.
Waiting for organizer confirmation.
```

No gathering occurs yet.

This is only informational.

---

## 4. Organizer Starts Gathering

Organizer manually presses:

```text
Start Gathering
```

This transitions the proposal into Gathering state.

Notifications are sent to all registered players.

Example:

```text
Blood on the Clocktower is gathering.

Location:
Table 17

Please respond.

[I'm Coming]
[Can't Make It]
```

---

## 5. Player Response

Players respond using notification links or buttons.

Possible responses:

```text
Coming
Can't Make It
```

The organizer sees a live attendance count.

Example:

```text
Registered: 12
Coming: 9
Declined: 3
```

---

## 6. Final Start

When sufficient players have confirmed:

```text
Ready to Start
```

The organizer gathers players and begins the game.

The proposal can be marked as:

```text
Started
```

or

```text
Closed
```

---

# State Machine

## Game States

```text
Draft
    ↓

Open
    ↓

Minimum Reached
    ↓

Gathering
    ↓

Started
```

Possible termination paths:

```text
Open
    → Closed

Minimum Reached
    → Closed

Gathering
    → Closed
```

---

# Notification Architecture

## Requirements

Notification methods should be independent from core game logic.

The coordinator should never directly send emails, DMs, or SMS messages.

Instead it emits events.

---

## High-Level Design

```text
Coordinator
     ↓

 Event Bus
     ↓

Notification Manager
     ↓

Providers
```

Providers:

```text
Email
Discord
Telegram
Web Push
SMS
```

---

## Provider Interface

Conceptually every provider should support:

```python
verify()
send()
```

Responsibilities:

- User onboarding
- Validation
- Message delivery

---

# Notification Providers

## Email

Registration flow:

1. User enters email.
2. Verification email sent.
3. User confirms ownership.

Capabilities:

- Confirmation messages
- Gathering notifications
- Attendance links

Initial priority: High

---

## Discord

Registration flow:

1. User links Discord account.
2. Bot validates messaging capability.
3. User becomes reachable via DM.

Capabilities:

- Direct messages
- Interactive buttons
- Rich status updates

Initial priority: High

---

## Telegram

Registration flow:

1. User opens bot.
2. User links account using token.
3. Bot records Telegram ID.

Initial priority: Medium

---

## Web Push Notifications

Registration flow:

1. User enables notifications.
2. Browser subscription stored.

Capabilities:

- Browser notifications
- Mobile push notifications

Initial priority: Medium

---

## SMS

Registration flow:

1. User enters phone number.
2. Number verified.

Capabilities:

- Critical notifications

Initial priority: Low

Reason:

- Cost per message.

---

# Verification Process

Every notification provider owns its own verification process.

Examples:

## Email

```text
Verification Code
```

## Discord

```text
OAuth Login
```

or

```text
Bot DM Verification
```

## Telegram

```text
Bot Start Token
```

## Web Push

```text
Browser Subscription
```

This logic should not exist in the core coordination system.

---

# Event-Driven Design

The coordinator emits domain events.

Example events:

```text
GameCreated
PlayerJoined
PlayerLeft
MinimumReached
GatheringStarted
AttendanceConfirmed
AttendanceDeclined
GameStarted
GameClosed
```

Notification providers subscribe to events.

Benefits:

- Low coupling
- Easier testing
- Easier future integrations

---

# Data Model

## Game

```text
Id
Title
Description
Organizer
Minimum Players
Ideal Players
Maximum Players
Location
Status
Created At
Updated At
```

---

## Player

```text
Id
Display Name
Created At
```

---

## Registration

Represents a player joining a game.

```text
Id
Game Id
Player Id
State
Joined At
```

Possible states:

```text
Registered
Coming
Declined
Withdrawn
```

---

## Notification Endpoint

Represents a verified way to contact a player.

```text
Id
Player Id
Provider
Address
Verified
```

Examples:

```text
Email
Discord
Telegram
SMS
WebPush
```

---

# MVP Scope

## Included

- Create game proposal
- QR code generation
- Join game
- Leave game
- Minimum player tracking
- Organizer notification
- Gathering mode
- Attendance confirmation
- Email notifications
- Discord notifications
- Mobile-friendly web UI

---

## Deferred

- SMS
- Telegram
- Web Push
- Convention-wide administration
- Event calendars
- Attendance statistics
- Recurring games
- Multi-convention support

---

# Suggested Technology Stack

## Backend

```text
Python
FastAPI
SQLAlchemy
Alembic
SQLite
```

SQLite should be sufficient for early development.

---

## Frontend

```text
Jinja2
HTMX
Bootstrap or PicoCSS
```

Goals:

- Mobile-friendly
- Minimal JavaScript
- Fast development

---

## Background Jobs

```text
APScheduler
```

or

```text
Celery
```

depending on future scale requirements.

---

## Notifications

```text
Email:
    SMTP / Mailgun / SendGrid

Discord:
    discord.py
```

---

# Future Possibilities

## Generalized Activities

Rename "Game" to "Activity" internally.

Potential activity examples:

- BOTC
- Board game
- RPG session
- CCG draft
- Meetup

---

## Convention Mode

Support multiple simultaneous activities.

Features:

- Venue maps
- Table assignments
- Capacity tracking
- Volunteer coordination

---

## PWA Support

Future enhancement.

Advantages:

- Faster access
- Push notifications
- Home screen installation

The system should not depend on PWA installation for core functionality.

---

# Success Criteria

The MVP is considered successful if:

1. An organizer can create a BOTC game.
2. Players can sign up through a QR code.
3. The organizer is notified when minimum players is reached.
4. The organizer can initiate gathering.
5. Players can confirm or decline attendance.
6. Notifications work via email and Discord.
7. The entire workflow functions from a mobile browser.
