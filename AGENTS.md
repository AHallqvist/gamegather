# Agent Documentation: GameGather

This document provides essential context for AI agents working on the GameGather codebase. It focuses on non-obvious architecture, conventions, and workflows to minimize trial-and-error.

## Project Overview
GameGather is a Python-based MVP for organizing social games (e.g., Blood on the Clocktower). The core principle is that **interest does not equal commitment**. The application manages the lifecycle from game proposal (interest) to the "gathering" phase (commitment).

## Core Architecture & Data Flow

### Layered Architecture
The project follows a simplified layered architecture:
- **API Layer (`app/src/main.py`)**: FastAPI routes. Handles HTTP requests/responses and Pydantic validation. Should *not* contain business logic.
- **Service Layer (`app/src/services/`)**: Contains the core business logic. This is where state transitions and complex rules reside.
- **Database Layer (`app/src/database.py`)**: Manages SQLite connections and schema initialization.
- **Notification Layer (`app/src/services/notification_service.py`)**: Decouples notification triggering from notification delivery.

### State Machine (Game Status)
Games transition through these primary states:
1. `draft`: Initial creation.
2. `open`: Proposal is public and accepting player interest.
3. `minimum_reached`: (Conceptual/Internal) Interest threshold met, waiting for organizer.
4. `gathering`: Organizer has started the gathering phase; players are prompted for attendance.
5. `started` / `closed`: Finalized states.

### Key Data Flows
- **Registration**: Player $\rightarrow$ API $\rightarrow$ `game_service` $\rightarrow$ Database (`registrations` table).
- **Notifications**: Logic triggers `queue_notification` $\rightarrow$ Database (`notifications` table with `queued` status). A separate process (simulated in `process_notifications`) is responsible for delivery.

## Development Workflow

### Environment & Setup
- **Prerequisites**: Docker and Docker Compose.
- **Environment Variables**: Copy `.env.example` to `.env`.
- **Running the App**:
  ```bash
  docker compose up --build
  ```
- **Database**: Uses SQLite. The database file is located at `data/gamegather.db` (within the container/project structure).

### Essential Commands
- **Build/Run**: `docker compose up --build`
- **Stop**: `docker compose down`

## Coding Conventions & Patterns

### Database Access
- Always use `get_connection()` from `src.database` to ensure `row_factory = sqlite3.Row` is applied (allows accessing columns by name).
- Use context managers (`with get_connection() as conn:`) to ensure connections are closed and transactions are handled.
- **Note**: The `init_db()` function must be called at application startup (handled in `main.py`).

### Service Layer Pattern
- Services should return dictionaries or plain data objects, not raw database rows, to maintain layer separation.
- Business logic involving multiple database steps should be encapsulated in a single service function to ensure atomicity.

### Non-Obvious Gotchas
- **Soft Deletes**: The `registrations` table uses `is_active` (integer 0/1) and `left_at` instead of deleting rows. When querying for active players, you **must** filter by `is_active = 1`.
- **Notification Decoupling**: Never call a third-party API (Discord, Email) directly inside a game service function. Always use `queue_notification` to record the intent in the database first.
- **SQLite Types**: Dates and times are stored as ISO 8601 strings in TEXT columns.

### Naming & Style
- Follow standard PEP 8 for Python.
- Function names in services should be descriptive of the action (e.g., `create_registration` vs `add_player`).
- Use type hints for all function signatures.

## Testing Strategy
*(Note: Current codebase lacks a formal test suite. New features should include unit tests for the Service layer.)*
