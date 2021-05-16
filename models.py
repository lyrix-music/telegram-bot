from spotipy import SpotifyOAuth


class User:
    def __init__(
            self,
            telegram_user_id: int = None,
            spotify_email_id: str = None,
            spotify_auth_token: str = None
    ):
        self.telegram_user_id = telegram_user_id
        self.spotify_email_id = spotify_email_id
        self.spotify_auth_token = spotify_auth_token

    @classmethod
    def from_dict(cls, data):
        return User(
            telegram_user_id=data.get("tg_id"),
            spotify_email_id=data.get("spot_id"),
            spotify_auth_token=data.get("spot_auth_token")
        )

    def parse_to_dict(self):
        return {
            "tg_id": self.telegram_user_id,
            "spot_id": self.spotify_email_id,
            "spot_auth_token": self.spotify_auth_token
        }

    def get_access_token(self, spo: SpotifyOAuth) -> str:
        token = spo.get_access_token(self.spotify_auth_token)
        return token.get("access_token")
