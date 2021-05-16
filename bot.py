
import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from urllib.parse import urlencode
from dotenv import load_dotenv

from lyrix.bot.app import LyrixApp
from lyrix.bot.fetch import get_lyrics_for_user
from lyrix.bot.models import User

load_dotenv()


# the SCOPES required to access the information and blah blah
SCOPES = "user-read-email user-read-currently-playing"
client_id = os.environ["SPOTIPY_CLIENT_ID"]
client_secret = os.environ["SPOTIPY_CLIENT_SECRET"]
spo = SpotifyOAuth(scope=SCOPES, client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=spo)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

la = LyrixApp(spo)
la.load()


music_controller = [
    [
        InlineKeyboardButton("Play this song ▶️", callback_data="play_for_me"),
    ]
]


def help_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update: Update, ctx: CallbackContext) -> None:
    """Echo the user message."""
    try:
        if update.message.text != "$lx" or update.message.text != "$lyrix":
            return
    except AttributeError:
        return
    get_lyrics_for_user(la, update.message, ctx)


def register(update: Update, _: CallbackContext) -> None:
    """Register a user"""
    update.message.reply_text(
        'Click the button below to connect your spotify account to '
        'Lyrix. Do not paste the callback code in group chats. Paste the code '
        'in a private message with @lyrixxxbot only.',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(text='Register', url=spo.get_authorize_url())],
        ])
    )


def login(update: Update, ctx: CallbackContext) -> None:
    text_message = update.message.text.split(" ")
    print(text_message)
    code = text_message[-1]

    la.add_user(User(telegram_user_id=update.message.from_user.id, spotify_auth_token=code))
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
    dispatcher.add_handler(CommandHandler("login", login))

    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    la.write()


if __name__ == '__main__':
    main()


