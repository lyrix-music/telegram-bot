import json

from swaglyrics.cli import stripper
from lyrix.bot.logging import make_logger
import urllib
from lyrix.bot.models.song import Song
import os
from typing import Optional, Tuple
import requests



from lyrix.bot.models.user import LyrixUser

STORAGE_JSON_PATH = "spotify.json"
DEFAULT_DATA = {"version": 1, "users": []}


class LyrixApp:
    logger = make_logger("lyrix_app")

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

    def get_spotify_user_from_telegram_user(
        self, telegram_id: int
    ) -> Optional[LyrixUser]:
        for user in self.db["users"]:
            if user.get("telegram_user_id") == telegram_id:
                return LyrixUser.from_dict(user)
        return None

    def get_user(self, telegram_id: int) -> Optional[LyrixUser]:
        for user in self.db["users"]:
            if user.get("telegram_user_id") == telegram_id:
                return LyrixUser.from_dict(user)
        return None

    def get_track_info(self, song: Song, show_info: bool = False) -> Tuple[str, str]:
        last_fm_api_key = os.getenv("LAST_FM_API_KEY")
        if not last_fm_api_key:
            return "", ""
        if not song.track or not song.artist:
            return "", ""
        self.logger.info("Requesting Track information from Last.fm api")
        artist = song.artist
        if "," in artist:
            artist = artist.split(", ")[0]

        # clean the artist names with some popular substitutions
        artist = artist.replace("- Music", "")
        artist = stripper("", artist).rstrip("-").replace("-", " ")
        self.logger.info(f"Cleaned artist name from {song.artist} to {artist}")

        info = requests.get(
            "https://ws.audioscrobbler.com/2.0/?method=track.getInfo"
            "&api_key={API_KEY}&artist={artist}&track={track}&autocorrect=1"
            "&format=json".format(
                API_KEY=last_fm_api_key,
                artist=urllib.parse.quote_plus(artist),
                track=urllib.parse.quote_plus(song.track),
            )
        ).json()

        image_infographics = info.get("track", {}).get("album", {}).get("image", [])

        album_art = ""
        for image_info in image_infographics[::-1]:
            if image_info.get("#text"):
                album_art = image_info.get("#text")
                self.logger.info("Received Album Art for song")
                break

        wiki = ""
        if show_info:
            wiki = info.get("track", {}).get("wiki", {}).get("summary", "")
            while wiki.find("<a href") != -1:
                start_idx = wiki.find("<a href")
                end_idx = wiki.find("</a>")
                wiki = wiki[:start_idx] + wiki[end_idx + len("</a>") :]
                self.logger.info("Received Wiki information for the song")
                if "<a href" not in wiki:
                    break

        return album_art, wiki
