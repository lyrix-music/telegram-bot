from typing import Tuple, Optional

import spotipy
import telegram
from markupsafe import escape
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

    sp = spotipy.Spotify(auth=user.get_access_token())
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
    song_name = escape(track["item"]["name"].replace("-", "\-").replace(".", "\."))
    artist_names = [x["name"] for x in track["item"]["artists"]]
    logger.info(f"{song_name} by {', '.join(artist_names)}")

    return str(song_name), artist_names, track


def share_song_for_user(la: LyrixApp, message: Message, ctx: CallbackContext) -> None:
    logger.info(f"{message.from_user.first_name}({message.from_user.id}) "
                f"requested to share the currently playing song.")

    currently_playing = _get_current_playing_song(la, message, ctx)
    if not currently_playing:
        return

    first_name = message.from_user.first_name
    song_name, artist_names, track = currently_playing
    artist_names_str = escape(", ".join(artist_names))

    try:
        url = track["item"]["external_urls"]["spotify"]
        right_now = f"{first_name} is currently playing [{song_name} by {artist_names_str}]({url})"
        reply_markup = (
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=" ▶️ Play this",
                            url=f"{url}",
                        )
                    ]
                ]
            ),
        )
    except Exception:
        reply_markup = None
        right_now = (
            f"{first_name} is currently playing {song_name} by {artist_names_str}"
        )

    ctx.bot.send_message(
        message.chat_id,
        right_now,
        parse_mode=telegram.ParseMode.MARKDOWN_V2,
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
        right_now = f"Getting lyrics for [{song_name} by {artist_names_str}]({url})"
    except Exception:
        right_now = f"Getting lyrics for {song_name} by {artist_names_str}"

    ctx.bot.send_message(
        message.chat_id, right_now, parse_mode=telegram.ParseMode.MARKDOWN_V2
    )

    logger.debug(f"Trying to get the lyrics for {song_name} by {artist_names_str}")
    lyrics = get_lyrics(song_name, artist_names[0])
    if lyrics is None or not lyrics:
        logger.warn(f"Couldn't get the lyrics for {song_name} by {artist_names[0]}")
        ctx.bot.send_message(message.chat_id, "Couldn't find the lyrics. 😔😔😔")
        return

    ctx.bot.send_message(message.chat_id, lyrics)
    logger.info("Lyrics sent successfully.")
