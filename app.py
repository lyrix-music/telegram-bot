import json
import os
from typing import Optional

from lyrix.bot.models.user import LyrixUser

STORAGE_JSON_PATH = "spotify.json"
DEFAULT_DATA = {"version": 1, "users": []}


class LyrixApp:
    def __init__(self):
        self.db = DEFAULT_DATA.copy()
        os.makedirs(".cache", exist_ok=True)

    def load(self):
        if not os.path.exists(STORAGE_JSON_PATH):
            with open(STORAGE_JSON_PATH, "w") as fp:
                json.dump(DEFAULT_DATA, fp)

        with open(STORAGE_JSON_PATH) as fp:
            self.db.update(json.load(fp))

    def write(self):
        with open(STORAGE_JSON_PATH, "w") as fp:
            json.dump(self.db, fp)

    def add_user(self, user: LyrixUser):
        for u in self.db["users"]:
            if u.get("telegram_user_id") == user.telegram_user_id:
                u.update(user.parse_to_dict())
                return
        self.db["users"].append(user.parse_to_dict())

    def get_spotify_user_from_telegram_user(self, telegram_id: int) -> Optional[LyrixUser]:
        for user in self.db["users"]:
            if user.get("telegram_user_id") == telegram_id:
                return LyrixUser.from_dict(user)
        return None

    def get_user(self, telegram_id: int) -> Optional[LyrixUser]:
        for user in self.db["users"]:
            if user.get("telegram_user_id") == telegram_id:
                return LyrixUser.from_dict(user)
        return None

