import time
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


def create_game(organizer_id: int, title: str, min_players: int, ideal_players: int | None,
               max_players: int | None, location: str | None, duration_minutes: int | None,
               notes: str | None):
    """
    Create a new game proposal.

    This is the first key action that an organizer performs. It should save all of
    the game details and assign a public URL for players to visit.
    """
    public_url = f"/games/{int(time.time())}"
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO games (
                organizer_id, title, status, min_players, ideal_players,
                max_players, location, duration_minutes, notes, public_url,
                created_at, updated_at
            ) VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organizer_id,
                title,
                min_players,
                ideal_players,
                max_players,
                location,
                duration_minutes,
                notes,
                public_url,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "public_url": public_url}


def get_game(game_id: int):
    """
    Fetch one game and its active players.

    This is useful for the organizer dashboard and for the public page.
    Pseudocode:
        game = query games table by id
        if game not found: return None
        players = query active registrations joined with players
        return {game, players}
    """
    with get_connection() as conn:
        game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        if not game:
            return None
        players = conn.execute(
            """
            SELECT p.*
            FROM registrations r
            JOIN players p ON p.id = r.player_id
            WHERE r.game_id = ? AND r.is_active = 1
            """,
            (game_id,),
        ).fetchall()
        return {"game": dict(game), "players": [dict(row) for row in players]}


def count_active_players(game_id: int) -> int:
    """
    Count the number of players actively registered for a game.

    Pseudocode:
        query rows where game_id matches and is_active = 1
        return number of rows
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS player_count FROM registrations WHERE game_id = ? AND is_active = 1",
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


def create_registration(game_id: int, player_id: int, notes: str | None):
    """
    Add a player to a game if they are not already active in it.

    Pseudocode:
        check if player already has an active registration for this game
        if yes: return existing registration
        else insert a new row with is_active = 1
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM registrations WHERE game_id = ? AND player_id = ? AND is_active = 1",
            (game_id, player_id),
        ).fetchone()
        if existing:
            return {"id": existing["id"], "already_registered": True}

        cursor = conn.execute(
            "INSERT INTO registrations (game_id, player_id, notes, is_active) VALUES (?, ?, ?, 1)",
            (game_id, player_id, notes),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "already_registered": False}


def remove_registration(game_id: int, player_id: int) -> None:
    """
    Remove a player from a game without deleting the history.

    This should not permanently delete the row. Instead, mark the registration as
    inactive and record when they left.

    Pseudocode:
        update registrations
        set is_active = 0
        set left_at = now
        where game_id and player_id match
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE registrations SET is_active = 0, left_at = ? WHERE game_id = ? AND player_id = ? AND is_active = 1",
            (datetime.utcnow().isoformat(), game_id, player_id),
        )
        conn.commit()
