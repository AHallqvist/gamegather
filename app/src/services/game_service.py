import secrets
from datetime import datetime

from src.database import get_connection

# This file contains the main business logic for the app.
# It is the place to put the rules for games, registrations, and state transitions.
#
# The most important ideas in this project are:
# 1. A game moves through states: open -> minimum reached -> gathering -> started/closed
# 2. Players register interest, but interest is not the same as commitment
# 3. The organizer manually decides when to start gathering
#
# Pseudocode for the domain logic:
#   create_game():
#       validate required fields
#       create a new row in the games table
#       return the game id and public URL
#
#   create_registration():
#       if player is already active in this game, do nothing
#       else insert a new registration row
#
#   set_game_status():
#       update the current status of the game
#
#   remove_registration():
#       mark the registration as inactive instead of deleting it


def create_game(organizer_id: int, title: str, min_players: int):
    """
    Create a new game proposal.

    This is the first key action that an organizer performs. It should save the
    game details and generate the secret organizer link token.
    """
    organizer_token = secrets.token_urlsafe(24)
    created_at = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (
                organizer_id, title, status, min_players, organizer_token,
                created_at, updated_at
            ) VALUES (?, ?, 'open', ?, ?, ?, ?)
            """,
            (
                organizer_id,
                title,
                min_players,
                organizer_token,
                created_at,
                created_at,
            ),
        )
        conn.commit()
        game_id = cursor.lastrowid
        return {
            "id": game_id,
            "public_url": f"/games/{game_id}",
            "organizer_url": f"/organizer/games/{organizer_token}",
        }


def get_game(game_id: int):
    """
    Fetch one game and its active people.

    This is useful for the organizer dashboard and for the public page.
    Pseudocode:
        game = query games table by id
        if game not found: return None
        people = query registrations joined with people
        return {game, people}
    """
    with get_connection() as conn:
        game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if not game:
            return None
        people = conn.execute(
            """
            SELECT p.*
            FROM registrations r
            JOIN people p ON p.id = r.person_id
            WHERE r.game_id = ?
            """,
            (game_id,),
        ).fetchall()
        return {"game": dict(game), "people": [dict(row) for row in people]}


def count_active_players(game_id: int) -> int:
    """
    Count the number of people actively registered for a game.

    Pseudocode:
        query rows where game_id matches
        return number of rows
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS player_count FROM registrations WHERE game_id = ?",
            (game_id,),
        ).fetchone()
        return int(row["player_count"] or 0)


def set_game_status(game_id: int, status: str) -> None:
    """
    Update the state of a game.

    This is where the status machine lives.
    Example statuses:
        draft
        open
        minimum_reached
        gathering
        started
        closed
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE games SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), game_id),
        )
        conn.commit()


def create_registration(game_id: int, person_id: int, notes: str | None):
    """
    Add a person to a game if they are not already registered for it.

    Pseudocode:
        check if person already has a registration for this game
        if yes: return existing registration
        else insert a new row
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM registrations WHERE game_id = ? AND person_id = ?",
            (game_id, person_id),
        ).fetchone()
        if existing:
            return {"id": existing["id"], "already_registered": True}

        cursor = conn.execute(
            "INSERT INTO registrations (game_id, person_id, notes) VALUES (?, ?, ?)",
            (game_id, person_id, notes),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "already_registered": False}


def remove_registration(game_id: int, person_id: int) -> None:
    """
    Remove a person from a game by deleting the registration row.

    Pseudocode:
        delete from registrations
        where game_id and person_id match
    """
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE game_id = ? AND person_id = ?",
            (game_id, person_id),
        )
        conn.commit()
