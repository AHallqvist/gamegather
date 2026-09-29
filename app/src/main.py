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
    record_attendance,
    remove_registration,
    start_gathering,
)


init_db()

app = FastAPI(title="GameGather")


class CreateGameRequest(BaseModel):
    title: str
    min_players: int
    organizer_name: str
    organizer_notification_method: str
    organizer_notification_target: str


class CreateRegistrationRequest(BaseModel):
    display_name: str
    notification_method: str
    notification_target: str


class AttendanceRequest(BaseModel):
    response: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gamegather"}


@app.post("/games")
def create_game_endpoint(payload: CreateGameRequest) -> dict[str, Any]:
    game = create_game(
        title=payload.title,
        min_players=payload.min_players,
        organizer_name=payload.organizer_name,
        organizer_notification_method=payload.organizer_notification_method,
        organizer_notification_target=payload.organizer_notification_target,
    )
    return {"ok": True, "game": game}


@app.get("/games/{game_id}")
def get_game_endpoint(game_id: int) -> dict[str, Any]:
    result = get_game(game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return result


@app.post("/games/{game_id}/register")
def register_for_game(game_id: int, payload: CreateRegistrationRequest) -> dict[str, Any]:
    try:
        registration = create_registration(
            game_id=game_id,
            display_name=payload.display_name,
            notification_method=payload.notification_method,
            notification_target=payload.notification_target,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Game not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return {"ok": True, "registration": registration}


@app.delete("/registrations/{registration_id}")
def unregister_for_game(registration_id: int) -> dict[str, bool]:
    try:
        remove_registration(registration_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Registration not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return {"ok": True}


@app.post("/games/{game_id}/gather")
def start_gathering_endpoint(game_id: int) -> dict[str, Any]:
    try:
        result = start_gathering(game_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "Game not found" else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return {"ok": True, **result}


@app.post("/registrations/{registration_id}/attendance")
def submit_attendance(registration_id: int, payload: AttendanceRequest) -> dict[str, Any]:
    if payload.response not in {"coming", "declined"}:
        raise HTTPException(status_code=400, detail="response must be 'coming' or 'declined'")

    try:
        record_attendance(registration_id, payload.response)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"ok": True, "response": payload.response}


@app.get("/games/{game_id}/summary")
def game_summary(game_id: int) -> dict[str, Any]:
    result = get_game(game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return {
        "game": result["game"],
        "active_player_count": count_active_players(game_id),
        "registrations": result["registrations"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "3000")))
