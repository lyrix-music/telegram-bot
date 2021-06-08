import os
import re
import random
from datetime import datetime
from typing import Tuple

from spotipy import CacheFileHandler, SpotifyOAuth

from lyrix.bot.api import Api
from lyrix.bot.app import LyrixApp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Chat
from telegram.ext import (
    CallbackContext,
)
import swaglyrics.cli as sl

from lyrix.bot.constants import (
    NO_LYRICS_ERROR,
    WELCOME_MESSAGE,
    AUTHORIZED_MESSAGE,
    NOT_A_VALID_SONG_ERROR_MESSAGE,
    REGISTER_INTRO_MESSAGE,
    SCOPES,
    LOGIN_INTRO_MESSAGE,
)
from lyrix.bot.fetch import (
    share_song_for_user,
    get_lyrics_for_user,
    clear_playlist_from_spotify,
    share_playlist_from_spotify,
    play_song_with_spotify,
)
from lyrix.bot.logging import make_logger
from lyrix.bot.models.user import LyrixUser


lyrix_id_match = re.compile(r"lyrix@\((.*)\)")


def get_username_and_homeserver(user_id: str) -> Tuple[str, str]:
    return user_id.split("@")[0][1:], user_id.split("@")[1]


class CommandInterface:
    logger = make_logger("commands")

    def __init__(self, la: LyrixApp, prefix: str = "$lx"):
        self.la = la
        self.la.load()
        self.command_prefix = prefix

    def ping_command(self, update: Update, _: CallbackContext) -> None:
        """Send a message when the command /ping is issued."""
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) issues ping command"
        )
        dt = datetime.now()
        update.message.reply_text(
            f"pong! latency is {dt.date() - update.message.date.date()}"
        )

    def is_valid_command(self, message: str) -> bool:
        """
        Checks if a string command is actually a valid command
        """

        if (
            message.strip().startswith(f"{self.command_prefix} ")
            or message == f"{self.command_prefix}"
        ):
            return True
        return False

    def get_lyrics(self, update: Update, ctx: CallbackContext) -> None:
        """Send the lyrics of the song the user is playing on spotify"""
        get_lyrics_for_user(self.la, update.message, ctx)

    def share_song(self, update: Update, ctx: CallbackContext) -> None:
        """Share the information of the current listening songs with your friends, from spotify"""
        share_song_for_user(self.la, update.message, ctx)

    def get_local_lyrics(self, update: Update, ctx: CallbackContext) -> None:
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) "
            f"issues local lyrics song command"
        )
        user = self.la.get_user(telegram_id=update.message.from_user.id)
        if user is None:
            update.message.reply_text("You haven't logged in yet 👀")
            return
        song = Api.get_current_local_listening_song(user=user)

        ctx.bot.send_message(
            update.message.chat_id,
            f"Getting lyrics for <b>{song.track}</b> by <b>{song.artist}</b>",
            parse_mode="html",
        )

        artist = song.artist.replace("BTS (防弹少年团)", "BTS").replace("- Music", "")
        lyrics = sl.get_lyrics(song.track, artist)

        if lyrics is None or not lyrics:
            self.logger.warn(f"Couldn't get the lyrics for {song.track} by {artist}")
            ctx.bot.send_message(update.message.chat_id, NO_LYRICS_ERROR)
            return

        ctx.bot.send_message(update.message.chat_id, lyrics)

    def share_local_song(self, update: Update, ctx: CallbackContext) -> None:
        msg = ctx.bot.send_message(
            update.message.chat_id,
            f"Getting {update.message.from_user.first_name}'s current playing song 🚀",
        )
        """Share the information of the current listening song from local music player"""
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id})"
            f" issues local share song command"
        )
        user = self.la.get_user(update.message.from_user.id)
        if user is None:
            ctx.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=msg.message_id,
                text="You haven't logged in yet 👀",
            )
            return
        song = Api.get_current_local_listening_song(user)

        if not song.track or not song.artist:
            ctx.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=msg.message_id,
                text=f"{update.message.from_user.first_name} is not playing any local song",
            )
            return

        show_fact = bool(random.randint(0, 1))
        album_info = self.la.get_track_info(song, show_info=show_fact)
        album_art_info = ""
        if album_info[0]:
            album_art_info = f"<a href='{album_info[0]}'>🎵</a>"

        if album_info[1] and show_fact:
            album_art_info = f"{album_art_info}\n\n<b>Wiki 🧠</b>: {album_info[1]}"

        ctx.bot.edit_message_text(
            chat_id=update.message.chat_id,
            message_id=msg.message_id,
            text=f"{update.message.from_user.first_name} is now playing \n<b>{song.track}</b>\nby <b>{song.artist}</b> {album_art_info}",
            parse_mode="html",
        )

    @staticmethod
    def show_telegram_id(update: Update, _: CallbackContext) -> None:
        update.message.reply_text(f"{update.message.from_user.id}")

    def general_command(self, update: Update, ctx: CallbackContext) -> None:
        """Echo the user message."""
        try:
            if not self.is_valid_command(update.message.text):
                return
        except AttributeError:
            return
        commands = update.message.text.strip().split(" ")
        if len(commands) == 1:
            get_lyrics_for_user(self.la, update.message, ctx)
            return
        if len(commands) == 2:
            args = commands[-1].strip()
            if args == "share":
                share_song_for_user(self.la, update.message, ctx)
                return
            elif args == "ping":
                self.ping_command(update, ctx)
                return
            elif args == "local":
                self.get_local_lyrics(update, ctx)
        elif len(commands) == 3:
            if "local" in commands and "share" in commands:
                self.share_local_song(update, ctx)

    def clear_playlist(self, update: Update, ctx: CallbackContext) -> None:
        clear_playlist_from_spotify(self.la, update.message, ctx)

    def share_playlist(self, update: Update, ctx: CallbackContext) -> None:
        share_playlist_from_spotify(self.la, update.message, ctx)

    def update_spotify_token(self, update: Update, _: CallbackContext) -> None:
        token_parts = update.message.text.split()
        if len(token_parts) != 2:
            update.message.reply_text("Usage: <command> <token>")
            return
        spotify_token = token_parts[-1]
        user = self.la.get_user(update.message.from_user.id)
        if user is None:
            update.message.reply_text("You haven't logged in yet 👀")
            return
        if spotify_token:
            pass
        is_success = Api.send_spotify_token(user=user, spotify_token=spotify_token)
        update.message.reply_text(f"Spotify token updated?: {is_success}")

    def who_am_i(self, update: Update, _: CallbackContext) -> None:
        user = self.la.get_user(update.message.from_user.id)
        if user is None:
            update.message.reply_text("You haven't logged in yet 👀")
            return
        update.message.reply_text(
            f"<b>User:</b> {user.username}\n"
            f"<b>Homeserver:</b> {user.homeserver}\n"
            f"<b>Telegram Id:</b> {user.telegram_user_id}",
            parse_mode="html",
        )

    def telegram_id(self, update: Update, _: CallbackContext) -> None:
        update.message.reply_text(
            f"<b>Telegram Id:</b> {update.message.from_user.id}",
            parse_mode="html",
        )

    def start(self, update: Update, ctx: CallbackContext) -> None:
        text_message = update.message.text.split(" ")
        print(text_message)
        code = text_message[-1]
        if len(text_message) == 1:
            self.logger.info(
                f"{update.message.from_user.first_name}({update.message.from_user.id}) "
                f"issues /start command without args"
            )
            # the user doesnt know yet.. lets give a demo
            ctx.bot.send_message(
                update.message.chat_id,
                WELCOME_MESSAGE,
            )
            return

        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) "
            f"issues /start command with params"
        )

        username, hs, token = code.split(":")
        if not token:
            update.message.reply_text(
                "Login credentials seem to be wrong. "
                "Are you sure your username and password is correct?"
            )
            return
        self.la.add_user(
            LyrixUser(
                telegram_user_id=update.message.from_user.id,
                username=username,
                homeserver=hs,
                token=token,
            )
        )
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) "
            f"has registered with lyrix"
        )
        update.message.reply_text(AUTHORIZED_MESSAGE)
        """
        try:
            user_id, password = code.split()
        except Exception as e:
            update.message.reply_text(f"Couldn't login: {e}")
            return

        username, homeserver = get_username_and_homeserver(user_id)
        token = Api.login(username=username, password=password, homeserver=homeserver)
        if not token:
            update.message.reply_text("Login credentials seem to be wrong. "
                                      "Are you sure your username and password is correct?")
            return
        self.la.add_user(
            LyrixUser(telegram_user_id=update.message.from_user.id,
                      username=username, homeserver=homeserver,
                      token=token)
        )
        self.logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) "
                         f"has registered with lyrix")
        update.message.reply_text(AUTHORIZED_MESSAGE)
        """

    def add_to_playlist(self, update: Update, ctx: CallbackContext) -> None:
        if update.message.reply_to_message is None:
            update.message.reply_text(
                "Reply to a song with /playthis command, or /playthis followed by spotify URL"
            )
            return
        spotify_song = update.message.reply_to_message.text
        print(spotify_song)
        match = lyrix_id_match.findall(spotify_song)
        if len(match) != 1:
            update.message.reply_text(NOT_A_VALID_SONG_ERROR_MESSAGE)
            return
        song_uri = match[0]

        play_song_with_spotify(self.la, update.message, ctx, song_uri)

    def register(self, update: Update, _: CallbackContext) -> None:
        """Register a user"""
        if update.message.chat.type != Chat.PRIVATE:
            update.message.reply_text("This command can only be used in private chats")
            return
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) issues register command"
        )

        update.message.reply_text(
            REGISTER_INTRO_MESSAGE
            + f" If you are asked for a telegram id, your id is <b>{update.message.from_user.id}</b> 😉.",
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Register",
                            url=f"https://web.lyrix.srev.in/register?id={update.message.from_user.id}",
                        )
                    ],
                ]
            ),
        )

    def login(self, update: Update, _: CallbackContext) -> None:
        """Gets the token of a user"""
        self.logger.info(
            f"{update.message.from_user.first_name}({update.message.from_user.id}) issues login command"
        )

        update.message.reply_text(
            LOGIN_INTRO_MESSAGE,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Login",
                            url="https://web.lyrix.srev.in/login",
                        )
                    ],
                ]
            ),
        )

    def connect_spotify(self, update: Update, _: CallbackContext) -> None:
        """Gets the token of a user"""
        handler = CacheFileHandler(
            username=str(update.message.from_user.id),
            cache_path=os.path.join(
                os.getcwd(), ".cache", f"cache-{update.message.from_user.id}"
            ),
        )
        update.message.reply_text(
            "Click the button below to connect your spotify account to " "Lyrix.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Authorize Spotify",
                            url=SpotifyOAuth(
                                cache_handler=handler, scope=SCOPES
                            ).get_authorize_url(),
                        )
                    ],
                ]
            ),
        )
