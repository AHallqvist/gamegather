import os
import sqlite3


DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.getcwd(), "data", "gamegather.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection for the app."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the minimal tables needed for the MVP."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                min_players INTEGER NOT NULL,
                organizer_name TEXT NOT NULL,
                organizer_notification_method TEXT NOT NULL,
                organizer_notification_target TEXT NOT NULL,
                organizer_token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                notification_method TEXT NOT NULL,
                notification_target TEXT NOT NULL,
                attendance_token TEXT NOT NULL UNIQUE,
                attendance_response TEXT CHECK(attendance_response IN ('coming', 'declined')),
                responded_at TEXT,
                FOREIGN KEY (game_id) REFERENCES games(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                recipient_role TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                notification_method TEXT NOT NULL,
                notification_target TEXT NOT NULL,
                event_type TEXT NOT NULL,
                action_token TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                last_error TEXT,
                sent_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id)
            );
            """
        )
        conn.commit()
