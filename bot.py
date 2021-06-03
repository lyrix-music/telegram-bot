
import datetime
import os
import re
import hashlib
from typing import Tuple

import requests
import swaglyrics.cli as sl
from datetime import datetime

from spotipy import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    commandhandler,
)

from dotenv import load_dotenv

from lyrix.bot.app import LyrixApp
from lyrix.bot.commands import CommandInterface
from lyrix.bot.constants import SCOPES
from lyrix.bot.fetch import get_lyrics_for_user, share_song_for_user, play_song_with_spotify, \
    clear_playlist_from_spotify, share_playlist_from_spotify

from lyrix.bot.logging import setup_logging, make_logger
from lyrix.bot.constants import AUTHORIZED_MESSAGE, NOT_A_VALID_SONG_ERROR_MESSAGE, WELCOME_MESSAGE, \
    REGISTER_INTRO_MESSAGE

load_dotenv()


client_id = os.environ["SPOTIPY_CLIENT_ID"]
client_secret = os.environ["SPOTIPY_CLIENT_SECRET"]
lyrix_backend = os.environ["LYRIX_BACKEND"]

lyrix_backend_token = os.environ["LYRIX_BACKEND_TOKEN"]

setup_logging()


t_logger = make_logger("tg")






def send_commands(update: Update, _: CallbackContext, commands: list, suffix: str) -> None:
    text_message = "<b>Lyrix Help</b>\n"
    for command, help in commands:
        text_message += f"- /{command[0]}{suffix} - {help}\n"
    update.message.reply_text(text_message, parse_mode="html")


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.

    logger = make_logger("main")
    logger.info("Trying to login to telegram with token")
    updater = Updater(os.environ["TELEGRAM_BOT_TOKEN"])
    logger.info("Login successful")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    la = LyrixApp()
    prefix = os.getenv("LYRIX_PREFIX") or "$lx"
    suffix = os.getenv("LYRIX_SUFFIX") or ""

    ci = CommandInterface(la, prefix=prefix)

    commands = [
        [("ping", ci.ping_command), "Ping the bot to see its alive"],
        [("updatespotifytoken", ci.update_spotify_token), "Update your spotify token"],
        [("whoami", ci.who_am_i), "Who am I? Get the login details"],
        [("login", ci.start), "Create an authorization token to send to me"],
        [("register", ci.start), "Instruction to create a lyrix account."],
        [("start", ci.start), "Start the bot and get the initial registration instructions"],
        [("lyrix", ci.get_lyrics), "Get the lyrics of the current listening song on spotify."],
        [("locallyrix", ci.get_local_lyrics), "Get the local lyrix from lyrixd app from your "
                                              "desktop or mobile music player"],
        [("sharesong", ci.share_song), "Share your current listening song with your friends"],
        [("sharelocalsong", ci.share_local_song), "Share the song you are listening using lyrixd "
                                                  "app from your desktop or mobile music player."],
        [("addtoplaylist", ci.add_to_playlist), "Adds the song to your spotify playlist"],
        [("clearplaylist", ci.clear_playlist), "Clear the lyrix spotify playlist"],

        
    ]
    # on different commands - answer in Telegram
    for command, _ in commands:
        command_text, command_func = command
        command_text = command_text + suffix
        dispatcher.add_handler(CommandHandler(command_text, command_func))
    dispatcher.add_handler(CommandHandler(f"help{suffix}",
                                          lambda update, ctx: send_commands(update, ctx, commands, suffix)))

    # on non command i.e message - general_command the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, ci.general_command))

    logger.info("Bot is up, and is ready to receive commands.")

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    logger.info("Received terminate. Stopping")
    logger.info("Completing exit")

    logger.info("Writing files")
    la.write()
    logger.info("Exiting")


if __name__ == "__main__":
    main()
