import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import database, main
from src.services.game_service import (
    count_active_players,
    create_game,
    create_organizer_registration,
    create_registration,
    get_organizer_game,
    start_game,
    start_gathering,
)


class OrganizerRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for patcher in (
            patch.object(database, "DB_PATH", folder.name + "/test.db"),
            patch.dict(os.environ, {"EMAIL_ENABLED": "true"}, clear=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        database.init_db()
        self.game = create_game("Game", 2, "Organizer", "email", "organizer@example.com")
        self.token = self.game["organizer_url"].split("/")[-1]
        self.client = TestClient(main.app)

    def test_offline_players_confirmed_and_reach_gathering_minimum(self) -> None:
        create_organizer_registration(self.token, "  Alice  ")
        with self.assertRaisesRegex(ValueError, "Minimum players not reached"):
            start_gathering(self.token)
        create_organizer_registration(self.token, "Bob")
        self.assertEqual(count_active_players(self.game["id"]), 2)
        registrations = get_organizer_game(self.token)["registrations"]
        self.assertEqual([row["display_name"] for row in registrations], ["Alice", "Bob"])
        for row in registrations:
            self.assertEqual(row["notification_method"], "none")
            self.assertEqual(row["notification_target"], "")
            self.assertEqual(row["attendance_response"], "coming")
            self.assertTrue(row["responded_at"])
        self.assertEqual(start_gathering(self.token), {"status": "gathering"})
        self.assertEqual(start_game(self.token), {"status": "started"})
        with database.get_connection() as conn:
            notices = conn.execute("SELECT * FROM notifications").fetchall()
        self.assertEqual([row["event_type"] for row in notices], [
            "game_created", "minimum_players_reached",
        ])
        self.assertTrue(all(row["recipient_role"] == "organizer" for row in notices))

    def test_create_game_can_register_organizer_as_player(self) -> None:
        game = create_game(
            "Organizer plays", 1, "Organizer", "email", "organizer@example.com",
            organizer_is_player=True,
        )
        token = game["organizer_url"].split("/")[-1]
        result = get_organizer_game(token)
        self.assertEqual(len(result["registrations"]), 1)
        registration = result["registrations"][0]
        self.assertEqual(registration["display_name"], "Organizer")
        self.assertEqual(registration["notification_method"], "none")
        self.assertEqual(registration["notification_target"], "")
        self.assertEqual(registration["attendance_response"], "coming")
        self.assertEqual(count_active_players(game["id"]), 1)
        with database.get_connection() as conn:
            events = [row["event_type"] for row in conn.execute(
                "SELECT event_type FROM notifications WHERE game_id = ? ORDER BY id",
                (game["id"],),
            )]
        self.assertEqual(events, ["game_created", "minimum_players_reached"])

    def test_create_game_form_and_api_accept_organizer_player_option(self) -> None:
        new_game_page = self.client.get("/games/new").text
        self.assertIn('name="organizer_is_player"', new_game_page)
        self.assertIn("Add me as a player", new_game_page)
        form_response = self.client.post("/games/new", data={
            "title": "Form game",
            "min_players": "3",
            "organizer_name": "Form organizer",
            "notification_method": "email",
            "notification_target": "form@example.com",
            "organizer_is_player": "true",
        }, follow_redirects=False)
        self.assertEqual(form_response.status_code, 303)
        form_token = form_response.headers["location"].split("/")[-1]
        form_registrations = get_organizer_game(form_token)["registrations"]
        self.assertEqual([row["display_name"] for row in form_registrations], ["Form organizer"])

        api_response = self.client.post("/games", json={
            "title": "API game",
            "min_players": 3,
            "organizer_name": "API organizer",
            "organizer_notification_method": "email",
            "organizer_notification_target": "api@example.com",
            "organizer_is_player": True,
        })
        self.assertEqual(api_response.status_code, 200)
        api_token = api_response.json()["game"]["organizer_url"].split("/")[-1]
        api_registrations = get_organizer_game(api_token)["registrations"]
        self.assertEqual([row["display_name"] for row in api_registrations], ["API organizer"])

    def test_mixed_group_notifies_only_contactable_players(self) -> None:
        create_organizer_registration(self.token, "In person")
        create_registration(self.game["id"], "Online", "email", "player@example.com")
        create_organizer_registration(self.token, "Extra")
        start_gathering(self.token)
        # Even an unanswered offline registration must never enter the queue.
        with database.get_connection() as conn:
            conn.execute(
                "UPDATE registrations SET attendance_response = NULL WHERE notification_method = 'none'",
            )
        start_game(self.token)
        with database.get_connection() as conn:
            notices = conn.execute(
                "SELECT event_type, recipient_name FROM notifications WHERE recipient_role = 'registration'",
            ).fetchall()
            threshold_count = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE event_type = 'minimum_players_reached'",
            ).fetchone()[0]
        self.assertEqual([(row[0], row[1]) for row in notices], [
            ("registration_created", "Online"),
            ("gathering_started", "Online"), ("game_started", "Online"),
        ])
        self.assertEqual(threshold_count, 1)

    def test_invalid_names_tokens_and_closed_games_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Organizer link not found"):
            create_organizer_registration("invalid", "Player")
        for name in ("", "   "):
            with self.assertRaisesRegex(ValueError, "player's name"):
                create_organizer_registration(self.token, name)
        self.assertEqual(count_active_players(self.game["id"]), 0)
        for status in ("gathering", "started", "closed", "draft"):
            with database.get_connection() as conn:
                conn.execute("UPDATE games SET status = ? WHERE id = ?", (status, self.game["id"]))
            with self.assertRaisesRegex(ValueError, "Registration is closed"):
                create_organizer_registration(self.token, "Late")

    def test_threshold_queue_failure_rolls_back_registration(self) -> None:
        create_organizer_registration(self.token, "One")
        with database.get_connection() as conn:
            conn.executescript("""
                CREATE TRIGGER reject_threshold BEFORE INSERT ON notifications
                WHEN NEW.event_type = 'minimum_players_reached'
                BEGIN SELECT RAISE(ABORT, 'test failure'); END;
            """)
        with self.assertRaises(sqlite3.IntegrityError):
            create_organizer_registration(self.token, "Two")
        self.assertEqual(count_active_players(self.game["id"]), 1)

    def test_form_api_and_organizer_page(self) -> None:
        url = self.game["organizer_url"]
        self.assertIn("Add an in-person player", self.client.get(url).text)
        response = self.client.post(
            url + "/register-form", data={"display_name": "Alice"}, follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], url)
        response = self.client.post(url + "/register", json={"display_name": "Bob"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        page = self.client.get(url).text
        self.assertIn("In-person · Coming", page)
        self.assertIn("Start gathering", page)
        for suffix, body_type in (("register", "json"), ("register-form", "data")):
            response = self.client.post(
                url + "/" + suffix, **{body_type: {"display_name": " "}},
            )
            self.assertEqual(response.status_code, 400)
            response = self.client.post(
                "/organizer/games/invalid/" + suffix,
                **{body_type: {"display_name": "Player"}},
            )
            self.assertEqual(response.status_code, 404)
        response = self.client.post(
            self.game["public_url"] + "/register", json={"display_name": "Player"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.post(self.game["public_url"] + "/register", json={
            "display_name": "Player", "notification_method": "none", "notification_target": "",
        }).status_code, 400)
        start_gathering(self.token)
        self.assertNotIn("Add an in-person player", self.client.get(url).text)
        self.assertEqual(self.client.post(url + "/register", json={"display_name": "Late"}).status_code, 400)
        self.assertEqual(self.client.post(url + "/register-form", data={"display_name": "Late"}).status_code, 400)
