import os

from dotenv import load_dotenv
from telegram import (
    Update,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    InlineQueryHandler,
)

from lyrix.bot.app import LyrixApp
from lyrix.bot.commands import CommandInterface
from lyrix.bot.logging import setup_logging, make_logger

try:
    from lyrix.bot.external_commands import ExternalCommandInterface

    external_commands = True
except ModuleNotFoundError:
    external_commands = False

load_dotenv()

client_id = os.environ["SPOTIPY_CLIENT_ID"]
client_secret = os.environ["SPOTIPY_CLIENT_SECRET"]
lyrix_backend = os.environ["LYRIX_BACKEND"]

lyrix_backend_token = os.environ["LYRIX_BACKEND_TOKEN"]

setup_logging()

t_logger = make_logger("tg")


def send_commands(
    update: Update, _: CallbackContext, commands: list, suffix: str
) -> None:
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
        [("ping", ci.ping_command), "👀 Ping the bot to see its alive"],
        [("connect_spotify", ci.connect_spotify), "🎹 Connect spotify to lyrix."],
        [
            ("update_spotify_token", ci.update_spotify_token),
            "👩‍💻 Update your spotify token (advanced users only)",
        ],
        [("who_am_i", ci.who_am_i), " 🤔 Who am I? Get the login details "],
        [("telegram_id", ci.telegram_id), "🆔 Get your telegram ID"],
        [("login", ci.login), "🔐 Create an authorization token to send to me"],
        [("register", ci.register), "🗒 Instruction to create a lyrix account."],
        [
            ("start", ci.start),
            "💫 Start the bot and get the initial registration instructions",
        ],
        [
            ("lyrix", ci.get_lyrics),
            "📑 Get the lyrics of the current listening song on spotify.",
        ],
        [
            ("locallyrix", ci.get_local_lyrics),
            "📱 Get the local lyrix from lyrixd app from your "
            "desktop or mobile music player",
        ],
        [
            ("sharesong", ci.share_song),
            "🎉 Share your current listening song with your friends",
        ],
        [
            ("sharelocalsong", ci.share_local_song),
            "✨ Share the song you are listening using lyrixd "
            "app from your desktop or mobile music player.✨",
        ],
        [
            ("addtoplaylist", ci.add_to_playlist),
            "▶️ Adds the song to your spotify playlist",
        ],
        [("clearplaylist", ci.clear_playlist), "🗑 Clear the lyrix spotify playlist"],
    ]

    if external_commands:
        external_ci = ExternalCommandInterface()
        commands += external_ci.commands()

    # on different commands - answer in Telegram
    print("Available commands are:")
    for command, help_message in commands:
        command_text, command_func = command
        command_text = command_text + suffix
        print(f"{command_text} - {help_message}")
        dispatcher.add_handler(
            CommandHandler(command_text, command_func, run_async=True)
        )
    dispatcher.add_handler(
        CommandHandler(
            f"help{suffix}",
            lambda update, ctx: send_commands(update, ctx, commands, suffix),
            run_async=True,
        )
    )

    # on non command i.e message - general_command the message on Telegram
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, ci.general_command)
    )

    dispatcher.add_handler(InlineQueryHandler(ci.inlinequery))
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
