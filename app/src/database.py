import os
import sqlite3

# This file is the database layer for the project.
# It is responsible for opening SQLite connections and making sure the tables exist.
#
# In a class assignment, this is the place to explain:
# - what each table represents
# - how the app stores games, players, registrations, and attendance responses
# - how the application gets data in and out of SQLite
#
# Pseudocode:
#   1. choose the database file path
#   2. create the data directory if it does not exist
#   3. open a connection
#   4. create all needed tables if they are missing

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.getcwd(), "data", "gamegather.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """
    Return a SQLite connection for the app.

    This function is useful because every service can call it instead of duplicating
    the connection logic. That keeps the code organized and easier to understand.

    Pseudocode:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Create the necessary database tables when the app starts.

    This is the startup setup for the project. Without this step, the application
    would not know how to store games, players, attendance, or notifications.

    Pseudocode:
        connect to database
        run SQL to create tables if they do not exist
        save changes
    """
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                email TEXT,
                discord_user_id TEXT,
                notification_preferences TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organizer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                min_players INTEGER NOT NULL DEFAULT 0,
                ideal_players INTEGER,
                max_players INTEGER,
                location TEXT,
                duration_minutes INTEGER,
                notes TEXT,
                public_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organizer_id) REFERENCES organizers(id)
            );

            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                left_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                FOREIGN KEY (game_id) REFERENCES games(id),
                FOREIGN KEY (player_id) REFERENCES players(id)
            );

            CREATE TABLE IF NOT EXISTS attendance_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id INTEGER NOT NULL,
                response TEXT NOT NULL CHECK(response IN ('coming', 'declined')),
                responded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (registration_id) REFERENCES registrations(id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                sent_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id),
                FOREIGN KEY (player_id) REFERENCES players(id)
            );
            """
        )
        conn.commit()
