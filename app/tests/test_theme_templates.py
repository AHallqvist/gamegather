import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import database, main
from src.services.game_service import create_game, create_registration, get_organizer_game


class ThemeTemplateTests(unittest.TestCase):
    def test_shared_theme_control_and_early_script_on_every_page(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(
            database, "DB_PATH", folder + "/test.db",
        ), patch.dict(os.environ, {"EMAIL_ENABLED": "true"}, clear=True):
            database.init_db()
            game = create_game("Game", 1, "Organizer", "email", "organizer@example.com")
            create_registration(game["id"], "Player", "email", "player@example.com")
            token = game["organizer_url"].split("/")[-1]
            player = get_organizer_game(token)["registrations"][0]
            client = TestClient(main.app)
            pages = [
                client.get(url, headers={"accept": "text/html"})
                for url in (
                    "/", "/games/new", game["public_url"], game["organizer_url"],
                    "/attendance/" + player["attendance_token"], "/attendance/invalid",
                )
            ]
            pages.append(client.post("/attendance/" + player["attendance_token"] + "/withdraw"))
            for response in pages:
                with self.subTest(url=str(response.url)):
                    html = response.text
                    self.assertIn('<script src="/static/theme.js"></script>', html)
                    self.assertLess(html.index("/static/theme.js"), html.index("/static/styles.css"))
                    self.assertIn('for="theme-select"', html)
                    self.assertIn('id="theme-select"', html)
                    self.assertIn("data-theme-picker hidden", html)
            self.assertEqual(client.get("/static/theme.js").status_code, 200)
