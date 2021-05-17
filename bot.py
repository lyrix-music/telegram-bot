import datetime
import os

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
from lyrix.bot.logging import setup_logging, make_logger

load_dotenv()


client_id = os.environ["SPOTIPY_CLIENT_ID"]
client_secret = os.environ["SPOTIPY_CLIENT_SECRET"]

setup_logging()
la = LyrixApp()
la.load()

t_logger = make_logger("tg")


def ping_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    t_logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) issues ping command")
    dt = datetime.datetime.now()
    update.message.reply_text(
        f"pong! latency is {dt.date() - update.message.date.date()}"
    )


def get_lyrics(update: Update, ctx: CallbackContext) -> None:
    get_lyrics_for_user(la, update.message, ctx)


def share_song(update: Update, ctx: CallbackContext) -> None:
    share_song_for_user(la, update.message, ctx)


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
        elif args == "ping":
            ping_command(update, ctx)
            return


def register(update: Update, _: CallbackContext) -> None:
    """Register a user"""
    t_logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) issues register command")
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
        t_logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) "
                      f"issues /start command without args")
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

    t_logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) "
                  f"issues /start command with params")
    la.add_user(
        User(telegram_user_id=update.message.from_user.id, spotify_auth_token=code)
    )
    t_logger.info(f"{update.message.from_user.first_name}({update.message.from_user.id}) has registered with lyrix")
    update.message.reply_text("✅ You are now authorized!")



def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.

    logger = make_logger("main")
    logger.info("Trying to login to telegram with token")
    updater = Updater(os.environ["TELEGRAM_BOT_TOKEN"])
    logger.info("Login successful")

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("ping", ping_command))
    dispatcher.add_handler(CommandHandler("register", register))
    dispatcher.add_handler(CommandHandler("start", login))
    dispatcher.add_handler(CommandHandler("lyrix", get_lyrics))
    dispatcher.add_handler(CommandHandler("sharesong", share_song))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

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
