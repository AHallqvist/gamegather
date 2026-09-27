# GameGather

A Python-first MVP for organizing pick-up games with an initial focus on BOTC-style gatherings.

## Quick start

1. Copy `.env.example` to `.env` and adjust values.
2. Build and run:

```bash
docker compose up --build
```

3. Open http://localhost:3000

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
