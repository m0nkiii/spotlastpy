#!/usr/bin/env python
import os
import pylast
import sqlite3
import spotipy
import spotipy.util as util
import logging

WRITE_CSV = 1

LASTFM_DATA = {'API_KEY': 'YOUR_API_KEY',
         'API_SECRET': 'YOUR_API_SECRET',
         'username': 'YOUR_LAST_FM_USERNAME'}

SPOTIFY_ENABLE = 1

SPOTIFY_DATA = {'CLIENT_ID': 'CLIENT_ID',
         'CLIENT_SECRET': 'CLIENT_SECRET',
         'REDIRECT_URI': 'http://localhost:8888/callback/',
         'scope': 'playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-follow-read user-library-read user-top-read',
         'username': 'YOUR_SPOTIFY_USERNAME'}

SPOTIFY_PLAYLISTS = {}

LASTFM_API = pylast.LastFMNetwork(api_key=LASTFM_DATA['API_KEY'], api_secret=LASTFM_DATA['API_SECRET'], username=LASTFM_DATA['username'])

DATABASE = sqlite3.connect(f"lastfm_{LASTFM_DATA['username']}.db")

c = DATABASE.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS lastfm_scrobbles (  id integer PRIMARY KEY AUTOINCREMENT,
                                                            artist text,
                                                            title text,
                                                            album text,
                                                            timestamp integer,
                                                            loved int default 0,
                                                            duration int default 0);
                                                            ''')
DATABASE.commit()

# Do not forget to close the connection at the end of the script

if SPOTIFY_ENABLE:
    token = util.prompt_for_user_token(SPOTIFY_DATA['username'], SPOTIFY_DATA['scope'], SPOTIFY_DATA['CLIENT_ID'], SPOTIFY_DATA['CLIENT_SECRET'], SPOTIFY_DATA['REDIRECT_URI'])

    if token:
        SPOTIFY_API = spotipy.Spotify(auth=token)
        SPOTIFY_API.trace = False
    else:
        print(f"Can't get token for {SPOTIFY_DATA['username']}")


    # logging.basicConfig(level=logging.DEBUG)
