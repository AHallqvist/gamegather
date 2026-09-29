import secrets
from datetime import datetime
from typing import Any

from src.database import get_connection
from src.services.notification_service import queue_notification


def create_game(
    title: str,
    min_players: int,
    organizer_name: str,
    organizer_notification_method: str,
    organizer_notification_target: str,
) -> dict[str, Any]:
    """Create a new game and queue an organizer confirmation notification."""
    organizer_token = secrets.token_urlsafe(24)
    created_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (
                title,
                status,
                min_players,
                organizer_name,
                organizer_notification_method,
                organizer_notification_target,
                organizer_token,
                created_at,
                updated_at
            ) VALUES (?, 'open', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                min_players,
                organizer_name,
                organizer_notification_method,
                organizer_notification_target,
                organizer_token,
                created_at,
                created_at,
            ),
        )
        conn.commit()
        game_id = cursor.lastrowid

    queue_notification(
        game_id=game_id,
        recipient_role="organizer",
        recipient_name=organizer_name,
        notification_method=organizer_notification_method,
        notification_target=organizer_notification_target,
        event_type="game_created",
    )

    return {
        "id": game_id,
        "public_url": f"/games/{game_id}",
        "organizer_url": f"/organizer/games/{organizer_token}",
    }


def list_open_games() -> list[dict[str, Any]]:
    """Fetch all open games."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT 
                id,
                title,
                status,
                min_players,
                organizer_name,
                created_at
            FROM games 
            WHERE status = 'open' 
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

def get_game(game_id: int) -> dict[str, Any] | None:
    """Fetch one game and its registrations."""
    with get_connection() as conn:
        game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if not game:
            return None

        registrations = conn.execute(
            "SELECT * FROM registrations WHERE game_id = ?",
            (game_id,),
        ).fetchall()
        return {
            "game": dict(game),
            "registrations": [dict(row) for row in registrations],
        }


def count_active_players(game_id: int) -> int:
    """Count current registrations for a game."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS player_count FROM registrations WHERE game_id = ?",
            (game_id,),
        ).fetchone()
        return int(row["player_count"] or 0)


def set_game_status(game_id: int, status: str) -> None:
    """Update the state of a game."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE games SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), game_id),
        )
        conn.commit()


def create_registration(
    game_id: int,
    display_name: str,
    notification_method: str,
    notification_target: str,
) -> dict[str, Any]:
    """Add a registration to an open game."""
    with get_connection() as conn:
        game = conn.execute(
            "SELECT * FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()
        if not game:
            raise ValueError("Game not found")
        if game["status"] != "open":
            raise ValueError("Registration is closed for this game")

        cursor = conn.execute(
            """
            INSERT INTO registrations (
                game_id,
                display_name,
                notification_method,
                notification_target,
                attendance_response,
                responded_at
            ) VALUES (?, ?, ?, ?, NULL, NULL)
            """,
            (game_id, display_name, notification_method, notification_target),
        )
        conn.commit()
        registration_id = cursor.lastrowid

    current_count = count_active_players(game_id)
    if current_count == int(game["min_players"]):
        queue_notification(
            game_id=game_id,
            recipient_role="organizer",
            recipient_name=game["organizer_name"],
            notification_method=game["organizer_notification_method"],
            notification_target=game["organizer_notification_target"],
            event_type="minimum_players_reached",
        )

    return {"id": registration_id}


def remove_registration(registration_id: int) -> None:
    """Remove a registration while the game is still open."""
    with get_connection() as conn:
        registration = conn.execute(
            """
            SELECT r.id, g.status
            FROM registrations r
            JOIN games g ON g.id = r.game_id
            WHERE r.id = ?
            """,
            (registration_id,),
        ).fetchone()
        if not registration:
            raise ValueError("Registration not found")
        if registration["status"] != "open":
            raise ValueError("Registration changes are locked for this game")

        conn.execute("DELETE FROM registrations WHERE id = ?", (registration_id,))
        conn.commit()


def start_gathering(organizer_token: str) -> dict[str, Any]:
    """Transition the organizer's game into gathering and queue notifications."""
    with get_connection() as conn:
        game = conn.execute(
            "SELECT * FROM games WHERE organizer_token = ?",
            (organizer_token,),
        ).fetchone()
        if not game:
            raise ValueError("Organizer link not found")
        if game["status"] != "open":
            raise ValueError("Game is not open for gathering")

        game_id = game["id"]
        registrations = conn.execute(
            "SELECT * FROM registrations WHERE game_id = ?",
            (game_id,),
        ).fetchall()
        if len(registrations) < int(game["min_players"]):
            raise ValueError("Minimum players not reached")

        conn.execute(
            "UPDATE games SET status = 'gathering', updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), game_id),
        )
        conn.commit()

    for registration in registrations:
        queue_notification(
            game_id=game_id,
            recipient_role="registration",
            recipient_name=registration["display_name"],
            notification_method=registration["notification_method"],
            notification_target=registration["notification_target"],
            event_type="gathering_started",
        )

    return {"status": "gathering"}


def record_attendance(registration_id: int, response: str) -> None:
    """Store a registration's attendance response."""
    with get_connection() as conn:
        registration = conn.execute(
            "SELECT id FROM registrations WHERE id = ?",
            (registration_id,),
        ).fetchone()
        if not registration:
            raise ValueError("Registration not found")

        conn.execute(
            "UPDATE registrations SET attendance_response = ?, responded_at = ? WHERE id = ?",
            (response, datetime.utcnow().isoformat(), registration_id),
        )
        conn.commit()
