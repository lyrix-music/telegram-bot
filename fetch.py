import spotipy
from swaglyrics.cli import get_lyrics
from telegram import Message
from telegram.ext import CallbackContext

from lyrix.bot.app import LyrixApp


def get_lyrics_for_user(la: LyrixApp, message: Message, ctx: CallbackContext):
    print(message.from_user.id)
    user = la.get_spotify_user_from_telegram_user(message.from_user.id)

    if user is None:
        ctx.bot.send_message(message.chat_id, "😔, I couldn't find you in my database. Have you registered yet?")
        return

    sp = spotipy.Spotify(auth=user.get_access_token(la.spotify_oauth))

    track = sp.current_user_playing_track()
    if not track['is_playing']:
        ctx.bot.send_message(message.chat_id, "Looks like you are not playing anything on Spotify.")
        return

    print(track)
    song_name = track["item"]["name"]
    artist_names = [x["name"] for x in track["item"]["artists"]]
    artist_names_str = ", ".join(artist_names)

    ctx.bot.send_message(message.chat_id, f"Getting lyrics for {song_name} by {artist_names_str}" )
    lyrics = get_lyrics(song_name, artist_names[0])
    if lyrics is None:
        ctx.bot.send_message(message.chat_id, "Couldn't find the lyrics. 😔😔😔")
        return
    ctx.bot.send_message(message.chat_id, lyrics)
    return track

