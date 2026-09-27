import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.database import init_db
from src.services.game_service import (
    count_active_players,
    create_game,
    create_registration,
    get_game,
    remove_registration,
    set_game_status,
)
from src.services.notification_service import queue_notification

# This file is the API entry point for the app.
# It is where the HTTP routes are defined for the web app.
#
# A class project would typically explain this file as:
# - the public interface for the system
# - the place where requests are received
# - the place where the app calls the service layer
#
# Pseudocode:
#   app = FastAPI()
#   initialize database
#   define routes for:
#       create game
#       get game
#       create player
#       register player for a game
#       start gathering
#       submit attendance
#       show summary

init_db()

app = FastAPI(title="GameGather")


class CreateGameRequest(BaseModel):
    """
    This request model is used when an organizer creates a new game proposal.

    Students can think of it as the form data submitted by the organizer.
    """
    organizer_id: int
    title: str
    min_players: int = 0
    ideal_players: int | None = None
    max_players: int | None = None
    location: str | None = None
    duration_minutes: int | None = None
    notes: str | None = None


class CreatePlayerRequest(BaseModel):
    """
    This models the data used to create a player account or player record.
    """
    display_name: str
    email: str | None = None
    discord_user_id: str | None = None
    notification_preferences: dict[str, Any] | None = None


class RegisterPlayerRequest(BaseModel):
    """
    This model is used when a player signs up to join a game.
    We only need the player_id and optional notes.
    """
    player_id: int
    notes: str | None = None


class AttendanceRequest(BaseModel):
    """
    This model captures a player's response to a gather request.
    Valid values are currently:
        - coming
        - declined
    """
    response: str


@app.get("/health")
def health() -> dict[str, str]:
    """
    A simple endpoint to confirm the server is running.

    Pseudocode:
        return {status: ok, service: gamegather}
    """
    return {"status": "ok", "service": "gamegather"}


@app.post("/games")
def create_game_endpoint(payload: CreateGameRequest) -> dict[str, Any]:
    """
    Create a new game by calling the game service.

    This endpoint represents the organizer creating a game proposal.
    """
    game = create_game(
        organizer_id=payload.organizer_id,
        title=payload.title,
        min_players=payload.min_players,
        ideal_players=payload.ideal_players,
        max_players=payload.max_players,
        location=payload.location,
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    return {"ok": True, "game": game}


@app.get("/games/{game_id}")
def get_game_endpoint(game_id: int) -> dict[str, Any]:
    """
    Read a single game and the players who are currently active.

    Pseudocode:
        game = get_game(game_id)
        if not found:
            return 404
        return game
    """
    result = get_game(game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return result


@app.post("/players")
def create_player(payload: CreatePlayerRequest) -> dict[str, Any]:
    """
    Create a player record.

    In a more complete app this might include validation, password handling, or
    notification onboarding. For this class project, we keep it simple.
    """
    from src.database import get_connection

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO players (display_name, email, discord_user_id, notification_preferences)
            VALUES (?, ?, ?, ?)
            """,
            (
                payload.display_name,
                payload.email,
                payload.discord_user_id,
                str(payload.notification_preferences or {}),
            ),
        )
        conn.commit()
        return {"ok": True, "player": {"id": cursor.lastrowid}}


@app.post("/games/{game_id}/register")
def register_for_game(game_id: int, payload: RegisterPlayerRequest) -> dict[str, Any]:
    """
    Register a player to a game.

    This endpoint is the key player action for the MVP. A player joins and becomes
    part of the interest count.
    """
    if not payload.player_id:
        raise HTTPException(status_code=400, detail="player_id is required")
    result = create_registration(game_id=game_id, player_id=payload.player_id, notes=payload.notes)
    return {"ok": True, "registration": result}


@app.delete("/games/{game_id}/register/{player_id}")
def unregister_for_game(game_id: int, player_id: int) -> dict[str, bool]:
    """
    Remove a player from a game.

    In the design, leaving is a valid action, and the system should not permanently
    delete their previous participation history.
    """
    remove_registration(game_id, player_id)
    return {"ok": True}


@app.post("/games/{game_id}/gather")
def start_gathering(game_id: int) -> dict[str, Any]:
    """
    Trigger the Gather phase for a game.

    Pseudocode:
        game.status = gathering
        find all active players in the registration table
        for each player:
            queue notification
        return success response
    """
    set_game_status(game_id, "gathering")
    from src.database import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT player_id FROM registrations WHERE game_id = ? AND is_active = 1",
            (game_id,),
        ).fetchall()

    for row in rows:
        queue_notification(game_id, row["player_id"], "gathering_started", "email")

    return {"ok": True, "status": "gathering"}


@app.post("/registrations/{registration_id}/attendance")
def submit_attendance(registration_id: int, payload: AttendanceRequest) -> dict[str, Any]:
    """
    Record whether a player is coming or declining.

    This is the final planner step before starting the game.
    """
    if payload.response not in {"coming", "declined"}:
        raise HTTPException(status_code=400, detail="response must be 'coming' or 'declined'")

    from src.database import get_connection

    with get_connection() as conn:
        registration = conn.execute(
            "SELECT * FROM registrations WHERE id = ?",
            (registration_id,),
        ).fetchone()
        if not registration:
            raise HTTPException(status_code=404, detail="Registration not found")

        conn.execute(
            "INSERT INTO attendance_responses (registration_id, response) VALUES (?, ?)",
            (registration_id, payload.response),
        )
        conn.commit()

    return {"ok": True, "response": payload.response}


@app.get("/games/{game_id}/summary")
def game_summary(game_id: int) -> dict[str, Any]:
    """
    Return the current summary for a game.

    This endpoint would be useful to the organizer dashboard to show:
        - current player count
        - who has joined
        - current game state
    """
    result = get_game(game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "game": result["game"],
        "active_player_count": count_active_players(game_id),
        "players": result["players"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "3000")))
