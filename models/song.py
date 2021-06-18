from typing import Union


class Song:
    def __init__(
        self,
        artist: Union[str, list] = "",
        track: str = "",
        source: str = "",
        url: str = "",
    ):
        self.artist = artist
        self.track = track
        self.source = source
        self.url = url

    @classmethod
    def from_json(cls, data: dict):
        return Song(
            artist=data["artist"],
            track=data["track"],
            url=data["url"],
            source=data["source"],
        )
