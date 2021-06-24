import os.path

from spotipy import SpotifyOAuth, CacheFileHandler

from lyrix_api.api import Api
from lyrix_bot.constants import SCOPES


class LyrixUser:
    def __init__(
        self,
        telegram_user_id: int = None,
        username: str = None,
        homeserver: str = None,
        token: str = None,
    ):
        self.telegram_user_id = telegram_user_id
        self.username = username
        self.homeserver = homeserver
        self.token = token
        self.playlist_id = None

    def parse_to_dict(self):
        return {
            "telegram_user_id": self.telegram_user_id,
            "username": self.username,
            "homeserver": self.homeserver,
            "token": self.token,
        }

    @classmethod
    def from_dict(cls, data):
        return LyrixUser(
            telegram_user_id=data.get("telegram_user_id"),
            username=data.get("username"),
            homeserver=data.get("homeserver"),
            token=data.get("token"),
        )

    def get_access_token(self) -> str:
        handler = CacheFileHandler(
            cache_path=os.path.join(
                os.getcwd(), ".cache", f"cache-{self.telegram_user_id}"
            ),
            username=str(self.telegram_user_id),
        )
        spo = SpotifyOAuth(cache_handler=handler, scope=SCOPES)
        spotify_auth_token = Api.get_spotify_token(self)

        token = spo.get_access_token(spotify_auth_token)
        return token.get("access_token")

    def set_user_playlist_queue(self, playlist_id: str) -> None:
        self.playlist_id = playlist_id


class User:
    def __init__(
        self,
        telegram_user_id: int = None,
        spotify_email_id: str = None,
        spotify_auth_token: str = None,
        playlist_id: str = None,
    ):
        self.telegram_user_id = telegram_user_id
        self.spotify_email_id = spotify_email_id
        self.spotify_auth_token = spotify_auth_token
        self.playlist_id = playlist_id

    @classmethod
    def from_dict(cls, data):
        return User(
            telegram_user_id=data.get("tg_id"),
            spotify_email_id=data.get("spot_id"),
            spotify_auth_token=data.get("spot_auth_token"),
            playlist_id=data.get("playlist_id"),
        )

    def parse_to_dict(self):
        return {
            "tg_id": self.telegram_user_id,
            "spot_id": self.spotify_email_id,
            "spot_auth_token": self.spotify_auth_token,
            "playlist_id": self.playlist_id,
        }

    def get_access_token(self) -> str:
        handler = CacheFileHandler(
            cache_path=os.path.join(
                os.getcwd(), ".cache", f"cache-{self.telegram_user_id}"
            ),
            username=str(self.telegram_user_id),
        )
        spo = SpotifyOAuth(cache_handler=handler, scope=SCOPES)

        token = spo.get_access_token(self.spotify_auth_token)
        return token.get("access_token")

    def set_user_playlist_queue(self, playlist_id: str) -> None:
        self.playlist_id = playlist_id
