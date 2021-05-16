import json
import os
from typing import Optional

import spotipy
from spotipy import SpotifyOAuth

from lyrix.bot.models import User

STORAGE_JSON_PATH = "spotify.json"
DEFAULT_DATA = {"version": 1, "users": []}


class LyrixApp:
    def __init__(self, spotify_oauth: SpotifyOAuth):
        self.db = DEFAULT_DATA.copy()
        self.spotify_oauth = spotify_oauth

    def load(self):
        if not os.path.exists(STORAGE_JSON_PATH):
            with open(STORAGE_JSON_PATH, 'w') as fp:
                json.dump(DEFAULT_DATA, fp)

        with open(STORAGE_JSON_PATH) as fp:
            self.db.update(json.load(fp))

    def write(self):
        with open(STORAGE_JSON_PATH, 'w') as fp:
            json.dump(self.db, fp)

    def add_user(self, user: User):
        self.db["users"].append(user.parse_to_dict())

    def get_spotify_user_from_telegram_user(self, telegram_id: int) -> Optional[User]:
        for user in self.db["users"]:
            if user.get("tg_id") == telegram_id:
                return User.from_dict(user)
        return None


