from html import escape
from typing import Tuple, Optional, Union

import spotipy
import telegram
import urllib.parse

from swaglyrics.cli import get_lyrics
from telegram import Message, InlineKeyboardMarkup, InlineKeyboardButton, User
from telegram.ext import CallbackContext

from lyrix_telegram_bot.app import LyrixApp
from lyrix_telegram_bot.logger import make_logger
from lyrix_telegram_bot.models.song import Song

logger = make_logger("core")


class LyrixSpotifyMetadata:
    def __init__(
        self, song: Song = None, track_info: dict = None, error_message: str = None
    ):
        self.song = song
        self.track_info = track_info
        self.error_message = error_message


def add_song_to_playlist(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    text_message = message.text
    commands = text_message.split(" ")
    if not commands[-1].startswith("spotify:"):
        ctx.bot.send_message(
            message.chat_id, "🤔 Looks like I can't understand what to play. Hmm.."
        )
        return

    spotify_track_uri = commands[-1]

    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    print(
        f"Getting currently playing song of {message.from_user.first_name} "
        f"{message.from_user.last_name} with id {message.from_user.id}"
    )
    try:
        sp = spotipy.Spotify(auth=user.get_access_token())
        sp.start_playback(context_uri=spotify_track_uri)
        ctx.bot.send_message(message.chat_id, "🚀 Ok oki. 😌👍")
        return
    except Exception as e:
        ctx.bot.send_message(
            message.chat_id,
            "Hmm. I wasn't able to play this song on your spotify client. "
            "Is your spotify running and connected? Perhaps you should try "
            "registering once again 🤷",
        )
        return


def _get_current_playing_song(
    la: LyrixApp,
    from_user: User,
) -> Optional[LyrixSpotifyMetadata]:
    user = la.get_spotify_user_from_telegram_user(from_user.id)

    if user is None:
        return LyrixSpotifyMetadata(
            error_message="😔, I couldn't find you in my database. Have you registered yet?"
        )
    try:
        spotify_auth_token = user.get_access_token()
    except spotipy.oauth2.SpotifyOauthError as e:
        return LyrixSpotifyMetadata(
            error_message=f"🙅, I couldn't authenticate with Spotify. {e}",
        )
    sp = spotipy.Spotify(auth=spotify_auth_token)
    logger.info(
        f"{from_user.first_name}({from_user.id}) " f"Authenticated with Spotify"
    )

    logger.info("Getting currently playing track on spotify")
    track = sp.current_user_playing_track()

    if track is None or not track["is_playing"]:
        logger.info(f"{from_user.first_name} is not playing anything on Spotify.")
        return LyrixSpotifyMetadata(
            error_message="Looks like you are not playing anything on Spotify."
        )

    elif track["item"] is None:
        # FIXME: not really sure
        logger.info(f"{from_user.first_name} is likely to be having ads now.")
        return LyrixSpotifyMetadata(error_message="😌👍 Ad time")

    # telegram doesnt like - character
    song_name = track["item"]["name"]
    artist_names = [x["name"] for x in track["item"]["artists"]]
    logger.info(f"{song_name} by {', '.join(artist_names)}")
    return LyrixSpotifyMetadata(
        song=Song(artist=artist_names, track=song_name), track_info=track
    )


def parse_spotify_data(song: LyrixSpotifyMetadata, from_user: User):
    track = song.track_info
    artist_names_str = escape(", ".join(song.song.artist))
    track_id = escape(track["item"]["uri"])

    try:
        url = song.track_info["item"]["external_urls"]["spotify"]
        right_now = f"""{from_user.first_name} is currently playing 
<a href='{url}'><b>{escape(song.song.track)}</b> by {artist_names_str}</a>

<i>lyrix@({track_id})</i>"""

        slug = f"{song.song.track} {artist_names_str}"
        slug_encoded = urllib.parse.quote(slug)
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="▶️ Play this",
                        url=f"{url}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="▶️ YT Music",
                        url=f"https://music.youtube.com/search?q={slug_encoded}",
                    ),
                    InlineKeyboardButton(
                        text="▶️ Spotify",
                        url=f"https://open.spotify.com/search/{slug_encoded}",
                    ),
                    InlineKeyboardButton(
                        text="▶️ Soundcloud",
                        url=f"https://soundcloud.com/search?q={slug_encoded}",
                    ),
                ],
            ]
        )

    except Exception:
        reply_markup = None
        right_now = (
            f"{from_user.first_name} is currently playing "
            f"{escape(song.song.track)} by {artist_names_str}"
        )
    return right_now, reply_markup


def share_song_for_user(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"requested to share the currently playing song."
    )

    currently_playing = _get_current_playing_song(la, from_user=message.from_user)
    if currently_playing.error_message:
        ctx.bot.send_message(message.chat_id, currently_playing.error_message)
        return
    if not currently_playing.song:
        return
    if not currently_playing.song.track:
        return

    right_now, reply_markup = parse_spotify_data(
        from_user=message.from_user, song=currently_playing
    )
    ctx.bot.send_message(
        message.chat_id,
        right_now,
        parse_mode=telegram.ParseMode.HTML,
        reply_markup=reply_markup,
    )
    return


def get_lyrics_for_user(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"requested for lyrics of the currently playing song."
    )

    spot_song = _get_current_playing_song(la, from_user=message.from_user)
    if spot_song.error_message:
        ctx.bot.send_message(message.chat_id, spot_song.error_message)
    if not spot_song.song:
        return
    if not spot_song.song.track:
        return

    track = spot_song.track_info
    song = spot_song.song

    artist_names_str = escape(", ".join(song.artist))

    try:
        url = track["item"]["external_urls"]["spotify"]
        right_now = (
            f"Getting lyrics for <a href='{url}'>{song.track} by {artist_names_str}</a>"
        )
    except Exception:
        right_now = f"Getting lyrics for {song.track} by {artist_names_str}"

    ctx.bot.send_message(message.chat_id, right_now, parse_mode=telegram.ParseMode.HTML)

    logger.debug(f"Trying to get the lyrics for {song.track} by {artist_names_str}")
    lyrics = get_lyrics(song.track, song.artist[0])

    if lyrics is None or not lyrics:
        logger.warn(f"Couldn't get the lyrics for {song.track} by {song.artist[0]}")
        ctx.bot.send_message(message.chat_id, "Couldn't find the lyrics. 😔😔😔")
        return

    ctx.bot.send_message(message.chat_id, lyrics)
    logger.info("Lyrics sent successfully.")


def play_song_with_spotify(
    la: LyrixApp, message: Message, ctx: CallbackContext, song: str
) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    try:
        sp = spotipy.Spotify(auth=user.get_access_token())
    except spotipy.oauth2.SpotifyOauthError as e:
        ctx.bot.send_message(
            message.chat_id,
            f"🙅, I couldn't authenticate with Spotify. {e}",
        )
        return

    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"Authenticated with Spotify"
    )

    if user.playlist_id is None:
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Attempting to create playlist"
        )
        playlist = sp.user_playlist_create(
            sp.me()["id"],
            "lyrix 🎧",
            public=False,
            collaborative=False,
            description="Lyrix song queue",
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Readding the user with the new playlist"
        )
        la.add_user(user)
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Playlist creation successful. Created with id {user.playlist_id}"
        )

    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"Attempting to add to playlist {song}"
    )
    sp.playlist_add_items(user.playlist_id, [song])
    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"Added {song} to playlist {user.playlist_id}"
    )

    message.reply_text("Added to queue 👌")


def clear_playlist_from_spotify(
    la: LyrixApp, message: Message, ctx: CallbackContext
) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    try:
        sp = spotipy.Spotify(auth=user.get_access_token())
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Authenticated with Spotify"
        )
    except spotipy.oauth2.SpotifyOauthError as e:
        ctx.bot.send_message(
            message.chat_id,
            f"🙅, I couldn't authenticate with Spotify. {e}",
        )
        return

    if user.playlist_id is None:
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Attempting to create playlist"
        )
        playlist = sp.user_playlist_create(
            sp.me()["id"],
            "lyrix 🎧",
            public=False,
            collaborative=False,
            description="Lyrix song queue",
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Readding the user with the new playlist"
        )
        la.add_user(user)
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Playlist creation successful. Created with id {user.playlist_id}"
        )

    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"Attempting to clear playlist {user.playlist_id}"
    )
    sp.playlist_replace_items(user.playlist_id, [])
    logger.info(
        f"{message.from_user.first_name}({message.from_user.id}) "
        f"Cleared playlist {user.playlist_id}"
    )

    message.reply_text("Cleared queue 🗑")


def share_playlist_from_spotify(
    la: LyrixApp, message: Message, ctx: CallbackContext
) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    if user.playlist_id is None:
        try:
            sp = spotipy.Spotify(auth=user.get_access_token())
        except spotipy.oauth2.SpotifyOauthError as e:
            ctx.bot.send_message(
                message.chat_id,
                f"🙅, I couldn't authenticate with Spotify. {e}",
            )
            return
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Authenticated with Spotify"
        )
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Attempting to create playlist"
        )
        playlist = sp.user_playlist_create(
            sp.me()["id"],
            "lyrix 🎧",
            public=False,
            collaborative=False,
            description="Lyrix song queue",
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Readding the user with the new playlist"
        )
        la.add_user(user)
        logger.info(
            f"{message.from_user.first_name}({message.from_user.id}) "
            f"Playlist creation successful. Created with id {user.playlist_id}"
        )

    message.reply_text(
        f"{message.from_user.first_name}'s playlist: "
        f"https://open.spotify.com/playlist/{user.playlist_id}"
    )
