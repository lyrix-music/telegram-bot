import json
from html import escape
from typing import Tuple, Optional

import spotipy
import telegram

from swaglyrics.cli import get_lyrics
from telegram import Message, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from lyrix.bot.app import LyrixApp
from lyrix.bot.logging import make_logger


logger = make_logger("core")


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
    la: LyrixApp, message: Message, ctx: CallbackContext
) -> Optional[Tuple[str, list, dict]]:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    spotify_auth_token = user.get_access_token()
    logger.info(f"Received spotify auth token: {spotify_auth_token}")
    sp = spotipy.Spotify(auth=spotify_auth_token)
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Authenticated with Spotify")

    logger.info("Getting currently playing track on spotify")
    track = sp.current_user_playing_track()

    if track is None or not track["is_playing"]:
        logger.info(f"{message.from_user.first_name} is not playing anything on Spotify.")
        ctx.bot.send_message(
            message.chat_id, "Looks like you are not playing anything on Spotify."
        )
        return
    elif track["item"] is None:
        # FIXME: not really sure
        logger.info(f"{message.from_user.first_name} is likely to be having ads now.")
        ctx.bot.send_message(message.chat_id, "😌👍 Ad time")
        return

    # telegram doesnt like - character
    song_name = track["item"]["name"]
    artist_names = [x["name"] for x in track["item"]["artists"]]
    logger.info(f"{song_name} by {', '.join(artist_names)}")
    return song_name, artist_names, track


def share_song_for_user(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"requested to share the currently playing song.")

    currently_playing = _get_current_playing_song(la, message, ctx)
    if not currently_playing:
        return

    first_name = message.from_user.first_name
    song_name, artist_names, track = currently_playing
    artist_names_str = escape(", ".join(artist_names))
    track_id = escape(track["item"]["uri"])

    try:
        url = track["item"]["external_urls"]["spotify"]
        right_now = f"""{first_name} is currently playing 
<a href='{url}'><b>{escape(song_name)}</b> by {artist_names_str}</a>

<i>lyrix@({track_id})</i>
        """
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="▶️ Play this",
                        url=f"{url}",
                    )
                ]
            ]
        )

    except Exception:
        reply_markup = None
        right_now = (
            f"{first_name} is currently playing {escape(song_name)} by {artist_names_str}"
        )

    ctx.bot.send_message(
        message.chat_id,
        right_now,
        parse_mode=telegram.ParseMode.HTML,
        reply_markup=reply_markup,
    )
    return


def get_lyrics_for_user(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"requested for lyrics of the currently playing song.")

    currently_playing = _get_current_playing_song(la, message, ctx)
    if not currently_playing:
        return

    song_name, artist_names, track = currently_playing
    artist_names_str = escape(", ".join(artist_names))

    try:
        url = track["item"]["external_urls"]["spotify"]
        right_now = f"Getting lyrics for <a href='{url}'>{song_name} by {artist_names_str}</a>"
    except Exception:
        right_now = f"Getting lyrics for {song_name} by {artist_names_str}"

    ctx.bot.send_message(
        message.chat_id, right_now, parse_mode=telegram.ParseMode.HTML
    )

    logger.debug(f"Trying to get the lyrics for {song_name} by {artist_names_str}")
    lyrics = get_lyrics(song_name, artist_names[0])
    if lyrics is None or not lyrics:
        logger.warn(f"Couldn't get the lyrics for {song_name} by {artist_names[0]}")
        ctx.bot.send_message(message.chat_id, "Couldn't find the lyrics. 😔😔😔")
        return

    ctx.bot.send_message(message.chat_id, lyrics)
    logger.info("Lyrics sent successfully.")


def play_song_with_spotify(la: LyrixApp, message: Message, ctx: CallbackContext, song: str) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    sp = spotipy.Spotify(auth=user.get_access_token())
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Authenticated with Spotify")

    if user.playlist_id is None:
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Attempting to create playlist")
        playlist = sp.user_playlist_create(
            sp.me()["id"], "lyrix 🎧", public=False, collaborative=False,
            description="Lyrix song queue"
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Readding the user with the new playlist")
        la.add_user(user)
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Playlist creation successful. Created with id {user.playlist_id}")

    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Attempting to add to playlist {song}")
    sp.playlist_add_items(user.playlist_id, [song])
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Added {song} to playlist {user.playlist_id}")

    message.reply_text("Added to queue 👌")


def clear_playlist_from_spotify(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    sp = spotipy.Spotify(auth=user.get_access_token())
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Authenticated with Spotify")

    if user.playlist_id is None:
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Attempting to create playlist")
        playlist = sp.user_playlist_create(
            sp.me()["id"], "lyrix 🎧", public=False, collaborative=False,
            description="Lyrix song queue"
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Readding the user with the new playlist")
        la.add_user(user)
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Playlist creation successful. Created with id {user.playlist_id}")

    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Attempting to clear playlist {user.playlist_id}")
    sp.playlist_replace_items(user.playlist_id, [])
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"Cleared playlist {user.playlist_id}")

    message.reply_text("Cleared queue 🗑")


def share_playlist_from_spotify(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(
            message.chat_id,
            "😔, I couldn't find you in my database. Have you registered yet?",
        )
        return

    if user.playlist_id is None:
        sp = spotipy.Spotify(auth=user.get_access_token())
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Authenticated with Spotify")
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Attempting to create playlist")
        playlist = sp.user_playlist_create(
            sp.me()["id"], "lyrix 🎧", public=False, collaborative=False,
            description="Lyrix song queue"
        )
        user.set_user_playlist_queue(playlist["id"])
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Readding the user with the new playlist")
        la.add_user(user)
        logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                    f"Playlist creation successful. Created with id {user.playlist_id}")

    message.reply_text(f"{message.from_user.first_name}'s playlist: "
                       f"https://open.spotify.com/playlist/{user.playlist_id}")
