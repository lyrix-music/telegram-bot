import os
import logging

from spotipy import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

from dotenv import load_dotenv

from lyrix.bot.app import LyrixApp
from lyrix.bot.constants import SCOPES
from lyrix.bot.fetch import get_lyrics_for_user, share_song_for_user
from lyrix.bot.models import User

load_dotenv()


client_id = os.environ["SPOTIPY_CLIENT_ID"]
client_secret = os.environ["SPOTIPY_CLIENT_SECRET"]


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

la = LyrixApp()
la.load()


music_controller = [
    [
        InlineKeyboardButton("Play this song ▶️", callback_data="play_for_me"),
    ]
]


def help_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("Help!")


def echo(update: Update, ctx: CallbackContext) -> None:
    """Echo the user message."""
    try:
        if (
            not update.message.text.startswith("$lx")
            and not update.message.text.startswith("$lyrix")
            and not update.message.text.startswith("$xl")
        ):
            return
    except AttributeError:
        return
    commands = update.message.text.strip().split(" ")
    if len(commands) == 1:
        get_lyrics_for_user(la, update.message, ctx)
        return
    if len(commands) == 2:
        args = commands[-1].strip()
        if args == "share":
            share_song_for_user(la, update.message, ctx)
            return


def register(update: Update, _: CallbackContext) -> None:
    """Register a user"""
    handler = CacheFileHandler(
        username=str(update.message.from_user.id),
        cache_path=os.path.join(
            os.getcwd(), ".cache", f"cache-{update.message.from_user.id}"
        ),
    )
    update.message.reply_text(
        "Click the button below to connect your spotify account to "
        "Lyrix. Do not paste the callback code in group chats. Paste the code "
        "in a private message with @lyrixxxbot only.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Register",
                        url=SpotifyOAuth(
                            cache_handler=handler, scope=SCOPES
                        ).get_authorize_url(),
                    )
                ],
            ]
        ),
    )


def login(update: Update, ctx: CallbackContext) -> None:
    text_message = update.message.text.split(" ")
    print(text_message)
    code = text_message[-1]
    if len(text_message) == 1:

        # the user doesnt know yet.. lets give a demo
        ctx.bot.send_message(
            update.message.chat_id,
            """Welcome to lyrix bot 🎵
        
To connect your Spotify account to Lyrix Bot, you will need to register.
Registration is possible using the /register command. Clicking the button 
will take you to a webpage and ask you to authorize lyrix bot with spotify.

This is necessary to help me receive your current playing song. 

Once Spotify authorization is completed, copy the telegram command code from the webpage
and paste it directly here 😌🤷.

Do not paste the auth code in telegram groups.""",
        )
        return

    la.add_user(
        User(telegram_user_id=update.message.from_user.id, spotify_auth_token=code)
    )
    update.message.reply_text("✅ You are now authorized!")
    print(la.db)


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.environ["TELEGRAM_BOT_TOKEN"])

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("register", register))
    dispatcher.add_handler(CommandHandler("start", login))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    la.write()


if __name__ == "__main__":
    main()
