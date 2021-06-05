# the SCOPES required to access the information and blah blah
SCOPES = "user-read-email user-read-currently-playing playlist-modify-public playlist-modify-private"


WELCOME_MESSAGE = """Welcome to lyrix bot 🎵
        
To login to your account, use the /login command 

Type /help for more information about other commands
"""

AUTHORIZED_MESSAGE = "✅ You are now authorized!"

NOT_A_VALID_SONG_ERROR_MESSAGE = "Not a valid song from lyrix. Can't play this."

NO_LYRICS_ERROR = "Couldn't find the lyrics. 😔😔😔"

REGISTER_INTRO_MESSAGE = (
    "Click the button below to create an account with Lyrix."
    "Do not share this link with anyone 😄"
)

LOGIN_INTRO_MESSAGE = (
    "For those who do not have a lyrix account yet, you should 'register' "
    "an account for yourself first. Use the button below to login to your lyrix "
    "account and generate an authorization token, which can be used by the bot "
    "to access information associated with your lyrix account (such as spotify token, "
    "currently listening song, etc.). Paste the code here once you are done. A sample authorization "
    "workflow would look like\n\n/start username:homeserver.com:4dd245b2322948dda9aaca9434469303"
)
