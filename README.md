# pyspotlast
Python Spotify Last fm

Uses pylast and spotipy

Purpose
------------

Download all Last.fm scrobble history.

Create Spotify playlists automatically

Run SQL queries to get all kinds of statistics.
https://sqlitebrowser.org/

How to start
------------

1. pip install -r requirement.txt
2. Add your information in config.py
3. Run get_first_scrobbles.py until you don't get any more scrobbles into database.
4. Edit update_scrobbles_and_playlists.py to your needs
5. python update_scrobbles_and_playlists.py
