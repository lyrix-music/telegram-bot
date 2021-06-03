class Song:
    def __init__(self, artist: str = "", track: str = ""):
        self.artist = artist
        self.track = track

    @classmethod
    def from_json(cls, data: dict):
        return Song(artist=data["artist"], track=data["track"])
