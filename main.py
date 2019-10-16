import sys
from enum import Enum
from datetime import datetime, timedelta
from datetime import date
import time
import csv
import os
import traceback

try:
    from my_config import LASTFM_DATA, LASTFM_API, \
        SPOTIFY_DATA, SPOTIFY_API, SPOTIFY_PLAYLISTS, SPOTIFY_ENABLE, \
        DATABASE, WRITE_CSV
except ImportError:
    from config import LASTFM_DATA, LASTFM_API, \
        SPOTIFY_DATA, SPOTIFY_API, SPOTIFY_PLAYLISTS, SPOTIFY_ENABLE, \
        DATABASE, WRITE_CSV


class UPDATE_MODE(Enum):
    GET_FIRST_SCROBBLE = 0
    UPDATE_DATABASE = 1

# ######################## HELP ##################################


def prev_week_range(when = None):
    """Return (previous week's start date, previous week's end date)."""
    today = datetime.today()
    weekday = today.weekday()

    start_delta = timedelta(days=weekday, weeks=1)
    end_delta = timedelta(days=6)

    start_of_week = today - start_delta
    end_of_week = start_of_week + end_delta

    return str(start_of_week), str(end_of_week)


def prev_month_range(when = None):
    """Return (previous month's start date, previous month's end date)."""
    if not when:
        # Default to today.
        when = datetime.today()
    # Find previous month: https://stackoverflow.com/a/9725093/564514
    # Find today.
    first = date(day=1, month=when.month, year=when.year)
    # Use that to find the first day of this month.
    prev_month_end = first - timedelta(days=1)
    prev_month_start = date(day=1, month= prev_month_end.month, year= prev_month_end.year)
    # Return previous month's start and end dates in YY-MM-DD format.
    return prev_month_start.strftime('%Y-%m-%d'), prev_month_end.strftime('%Y-%m-%d')

# ######################## LAST FM ################################


def update_database(number):
    thousands = int(number / 1000)
    rest = number - thousands * 1000
    for i in range(0,thousands):
        internal_get_recent_tracks(1000, UPDATE_MODE.UPDATE_DATABASE)

    if rest > 0:
        internal_get_recent_tracks(rest, UPDATE_MODE.UPDATE_DATABASE)


def get_all_scrobbles(number):
    thousands = int(number / 1000)
    rest = number - thousands * 1000
    for i in range(0,thousands):
        internal_get_recent_tracks(1000, UPDATE_MODE.GET_FIRST_SCROBBLE)

    if rest > 0:
        internal_get_recent_tracks(rest, UPDATE_MODE.GET_FIRST_SCROBBLE)


def internal_get_recent_tracks(number, mode):
    try:
        max_date = get_max_scrobble_time()
        min_date = get_min_scrobble_time()

        if mode == UPDATE_MODE.GET_FIRST_SCROBBLE:
            if min_date == 0:
                recent_tracks = LASTFM_API.get_user(
                    LASTFM_DATA['username']).get_recent_tracks(limit=number, time_from=0)
            else:
                recent_tracks = LASTFM_API.get_user(
                    LASTFM_DATA['username']).get_recent_tracks(limit=number, time_from=0, time_to=min_date)
        elif mode == UPDATE_MODE.UPDATE_DATABASE:
            recent_tracks = LASTFM_API.get_user(
                LASTFM_DATA['username']).get_recent_tracks(limit=number, time_from=max_date+1)

        count = 0
        values = []
    except Exception as e:
        print(e)
        raise

    for i, track in enumerate(recent_tracks):
        count +=1

        try:
            artist = str(track.track.artist)
            title = str(track.track.title)

            values.append((artist, title, track.album, track.timestamp))
        except Exception as e:
            print(e)
            raise

    try:
        c = DATABASE.cursor()

        print(f"Number of scrobbles added to database: {len(values)}")

        c.executemany("INSERT INTO lastfm_scrobbles(artist, title, album, timestamp) VALUES(?,?,?,?)", values)

        DATABASE.commit()
    except Exception as e:
        print(e)
        raise

    print(f"Count: {count}")
    return recent_tracks


def update_durations(limit):
    tracks = execute_sql_get_list(
        None,
        f'SELECT artist, title '
        f'FROM lastfm_scrobbles '
        f'WHERE duration = 0 '
        f'GROUP BY artist, title '
        f'ORDER BY count(*) DESC '
        f'LIMIT {limit}')

    values = []

    for track in tracks:
        t = LASTFM_API.get_track(track[0], track[1])
        duration = t.get_duration()
        values.append((duration, track[0], track[1]))

    execute_many_sql("UPDATE lastfm_scrobbles SET duration = ? WHERE artist = ? AND title = ?", values)


# Get recommended for an artist
# def lastfm_get_recommended_tracks(artist):
#    pass


def lastfm_get_recommended_tracks(artist, title, end_date='3000-01-01'):
    # print(f'lastfm_get_recommended_tracks: {artist}, {title}, {end_date}')
    track = LASTFM_API.get_track(artist, title)
    similar = track.get_similar(5)

    list_of_tracks = []

    for track in similar:
        # split_str = str(track.item).split('-', 1)
        # similar_artist = split_str[0].strip()
        # similar_title = split_str[1].strip()
        similar_artist = str(track.item.artist)
        similar_title = str(track.item.title)

        if not database_find_track_interval(similar_artist, similar_title, end_date):
            list_of_tracks.append([similar_artist, similar_title])

    return list_of_tracks


def lastfm_get_recommended_tracks_list(tracks, end_date):
    # print(f'lastfm_get_recommended_tracks_list: {end_date}')

    list_of_tracks = []

    for track in tracks:
        recommended_list = lastfm_get_recommended_tracks(track[0], track[1], end_date)
        for t in recommended_list:
            list_of_tracks.append([t[0], t[1]])

    return list_of_tracks

# ##################### DATABASE ###########################


def get_max_scrobble_time():
    c = DATABASE.cursor()
    c.execute(''' SELECT max(timestamp) FROM lastfm_scrobbles ''')

    data = c.fetchone()[0]

    if data is None:
        return 0
    else:
        print(f"Latest scrobble: {datetime.fromtimestamp(data)}")
        return int(data)


def get_min_scrobble_time():
    c = DATABASE.cursor()
    c.execute(''' SELECT min(timestamp) FROM lastfm_scrobbles ''')

    data = c.fetchone()[0]

    if data is None:
        return 0
    else:
        print(f"First scrobble: {datetime.fromtimestamp(data)}")
        return int(data)


def database_get_years():
    c = DATABASE.cursor()
    c.execute(''' SELECT DISTINCT(strftime('%Y', timestamp, 'unixepoch')) FROM lastfm_scrobbles ''')

    return c.fetchall()


def database_get_top_tracks(limit=0):
    c = DATABASE.cursor()
    # All tracks
    if limit == 0:
        print(f"Get all the top tracks")
        c.execute(f"SELECT artist, title, count(*) "
                  f"FROM lastfm_scrobbles "
                  f"GROUP BY artist, title "
                  f"ORDER BY count(*) DESC")
    # Limit it to a certain number
    else:
        print(f"Get the top {limit} tracks")
        c.execute(f"SELECT artist, title, count(*) "
                  f"FROM lastfm_scrobbles "
                  f"GROUP BY artist, title "
                  f"ORDER BY count(*) DESC "
                  f"LIMIT {limit}")

    return c.fetchall()


def database_get_top_albums(limit=0):

    c = DATABASE.cursor()
    # All tracks
    if limit == 0:
        print("Get all the top albums")
        c.execute(f"SELECT album, count(*) "
                  f"FROM lastfm_scrobbles "
                  f"WHERE album IS NOT NULL "
                  f"GROUP BY album "
                  f"ORDER BY count(*) DESC")
    # Limit it to a certain number
    else:
        print(f"Get the top {limit} albums")
        c.execute(f"SELECT album, count(*) "
                  f"FROM lastfm_scrobbles "
                  f"WHERE album IS NOT NULL "
                  f"GROUP BY album "
                  f"ORDER BY count(*) DESC "
                  f"LIMIT {limit}")
    return c.fetchall()


def database_get_top_artists(limit=0):
    c = DATABASE.cursor()
    # All artists
    if limit == 0:
        print(f"Get all the top artists")
        c.execute("SELECT DISTINCT(artist) "
                  "FROM lastfm_scrobbles "
                  "ORDER BY artist")
    # Limit it to a certain number
    else:
        print(f"Get the top {limit} artists")
        c.execute(f"SELECT artist, count(*) "
                  f"FROM lastfm_scrobbles "
                  f"GROUP BY artist "
                  f"ORDER BY count(*) DESC "
                  f"LIMIT {limit}")

    return c.fetchall()


def database_find_tracks_from_artist(artist):
    return execute_sql_get_list(f'all_my_tracks_from_{artist}',
        f"SELECT artist, title, count(*) "
        f"FROM lastfm_scrobbles "
        f"WHERE artist LIKE \"{artist}%\" "
        f"GROUP BY artist, title "
        f"ORDER BY count(*) DESC")


def database_find_track(artist, title):
    row = execute_sql_get_value(
        f"SELECT count(*) "
        f"FROM lastfm_scrobbles "
        f"WHERE artist LIKE \"{artist}%\" AND title LIKE \"{title}%\"")
    if row[0] == 0:
        return False
    else:
        return True


def database_find_track_interval(artist, title, end_date='3000-01-01'):
    dt = datetime.fromisoformat(end_date)
    end_date_unix = time.mktime(dt.timetuple())

    row = execute_sql_get_value(
        f"SELECT count(*) "
        f"FROM lastfm_scrobbles "
        f"WHERE artist LIKE ? AND title LIKE ? AND timestamp < {end_date_unix}", (artist+'%', title+'%'))
    if len(row) == 0 or (len(row) > 0 and row[0] == 0):
        return False
    else:
        return True


def execute_sql(s):
    c = DATABASE.cursor()
    try:
        c.execute(s)
        DATABASE.commit()
    except Exception as e:
        print(f"Exception when running {s}: {e}")


def execute_many_sql(s, values):
    c = DATABASE.cursor()
    try:
        c.executemany(s, values)
        DATABASE.commit()
    except Exception as e:
        print(f"Exception when running {s}: with values {values} : {e}")


def get_all_unique_tracks():
    pass


def execute_sql_get_list(name, s):
    print(f"execute_sql_get_list: ({name}) - {s}")

    try:
        if WRITE_CSV and name is not None:
            cursor_csv = DATABASE.cursor()
            cursor_csv.execute(s)

            filename = f"./CSV/{name}.csv"
            print(f'Write CSV file: {filename}')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", newline='', encoding="utf-8") as csv_file:
                csv_writer = csv.writer(csv_file, delimiter=';')
                # write headers
                csv_writer.writerow([f'"{i[0]}"' for i in cursor_csv.description])
                for row in cursor_csv.fetchall():
                    csv_writer.writerow([f'"{r}"' for r in row])

    except Exception as e:
        print(f"execute_sql_get_list - Exception when writing to CSV: {e}")

    try:
        c = DATABASE.cursor()
        c.execute(s)
    except Exception as e:
        print(f"execute_sql_get_list - Exception when executing {s}: {e}")
        return []

    rows = c.fetchall()

    print(f"execute_sql_get_list: ({name}) - length of list: {len(rows)}")
    return rows


def execute_sql_get_value(s):
    c = DATABASE.cursor()
    try:
        c.execute(s)
    except Exception as e:
        print(f"Exception when running {s}: {e}")
        return []

    row = c.fetchone()

    return row


def execute_sql_get_value(s, params):
    c = DATABASE.cursor()
    try:
        c.execute(s, params)
    except Exception as e:
        print(f"Exception when running {s} {params}: {e}")
        return []

    row = c.fetchone()

    return row

# ##################### SPOTIFY #############################


def prepare_string_for_search(s):
    s = s.replace('\'', '')
    s = s.replace('+', '')
    return s


def spotify_find_track(artist, title):
    artist = prepare_string_for_search(artist)
    title = prepare_string_for_search(title)

    search_str = 'artist:"' + str(artist) + '" track:"' + str(title) + '"'
    results = SPOTIFY_API.search(q=search_str, limit=1, type='track')

    try:
        track = results['tracks']['items'][0]
        # print(f"Track found on Spotify: {artist} - {title}")
        return track
    except:
        print(f"\nTrack NOT found on Spotify: {artist} - {title}\n")
        return None


def playlist_get_all():
    try:
        limit = 50
        count = 0
        playlists = SPOTIFY_API.user_playlists(SPOTIFY_DATA['username'], limit=limit, offset=0)
        while len(playlists['items']) != 0:
            for playlist in playlists['items']:
                SPOTIFY_PLAYLISTS[playlist['name']] = playlist['id']
            count += 1
            playlists = SPOTIFY_API.user_playlists(SPOTIFY_DATA['username'], limit=limit, offset=count*limit)
    except Exception as e:
        print(e)
        return None


def playlist_exists(p_name):
    try:
        print(f"playlist_exists: ({p_name})")
        exists = SPOTIFY_PLAYLISTS[p_name]
        print(f"playlist_exists: ({p_name}) does exist")
        return exists
    except Exception as e:
        print(f"playlist_exists: ({p_name}) does NOT exist")
        return None


def playlist_create(p_name):
    try:
        playlist = SPOTIFY_API.user_playlist_create(SPOTIFY_DATA['username'], p_name, True)
        print(f'playlist created: ({p_name})')
        return playlist['id']
    except Exception as e:
        print(f'playlist created: ({p_name}) was not created due to exception')
        return None


def spotify_find_list_of_tracks(list_of_track_name):
    list_of_track_uri = []
    count = 0

    for track in list_of_track_name:
        track = spotify_find_track(track[0], track[1])
        if track is not None:
            list_of_track_uri.append(track['uri'])
            count += 1

    print(f"{count} / {len(list_of_track_name)} was found and added")

    return list_of_track_uri


def playlist_replace_tracks_name(playlist_id, list_of_track_name):
    print(f"playlist_replace_tracks_name: {playlist_id} - length of list track names: {len(list_of_track_name)}")
    list_of_track_uri = spotify_find_list_of_tracks(list_of_track_name)
    playlist_replace_tracks_uri(playlist_id, list_of_track_uri)


def playlist_add_tracks_name(playlist_id, list_of_track_name):
    print(f"playlist_add_tracks_name: {playlist_id} - length of list track names: {len(list_of_track_name)}")
    list_of_track_uri = spotify_find_list_of_tracks(list_of_track_name)
    playlist_add_tracks_uri(playlist_id, list_of_track_uri)


def playlist_replace_tracks_uri(playlist_id, list_of_track_uri):
    print(f"playlist_add_tracks_name: {playlist_id} - length of list uri: {len(list_of_track_uri)}")
    for i in range(0, len(list_of_track_uri), 100):
        results = SPOTIFY_API.user_playlist_replace_tracks(SPOTIFY_DATA['username'],
                                                           playlist_id,
                                                           list_of_track_uri[i:i+100])


def playlist_add_tracks_uri(playlist_id, list_of_track_uri):
    print(f"playlist_add_tracks_uri: {playlist_id} - length of list uri: {len(list_of_track_uri)}")
    for i in range(0, len(list_of_track_uri), 100):
        results = SPOTIFY_API.user_playlist_add_tracks(SPOTIFY_DATA['username'],
                                                       playlist_id,
                                                       list_of_track_uri[i:i+100])


def spotify_get_artist(artist_name):
    results = SPOTIFY_API.search(q='artist:' + artist_name, limit=10, type='artist')

    try:
        for artist in results['artists']['items']:
            if artist['name'].lower() == artist_name.lower():
                return artist

        print(f"\nArtist NOT found on Spotify: {artist_name}\n")
        return None
    except:
        print(f"\nArtist NOT found on Spotify: {artist_name}\n")
        return None


def spotify_get_artist_top_tracks(artist_uri):
    artist = SPOTIFY_API.artist_top_tracks(artist_uri)

    tracks = []

    for track in artist['tracks'][:10]:
        tracks.append(track['uri'])

    return tracks


def spotify_get_recommended_tracks_list(tracks, end_date='3000-01-01'):
    # print(f'lastfm_get_recommended_tracks_list: {end_date}')

    list_of_tracks = []

    tracks_uri = spotify_find_list_of_tracks(tracks)
    for track in tracks_uri:
        tracks_recommended = SPOTIFY_API.recommendations(seed_tracks=[track], limit=5)
        for rec_track in tracks_recommended['tracks']:
            if not database_find_track_interval(rec_track['artists'][0]['name'], rec_track['name'], end_date):
                list_of_tracks.append(rec_track['uri'])

    return list_of_tracks


# ################ Playlists #####################


def create_playlist_and_add_tracks(p_name, tracks):
    if SPOTIFY_ENABLE:
        playlist_id = playlist_exists(p_name)

        if playlist_id is None:
            playlist_id = playlist_create(p_name)
            playlist_add_tracks_name(playlist_id, tracks)


def create_playlist_from_sql(p_name, s, replace_tracks=1):
    if 'SELECT artist, title' not in s:
        raise Exception('SQL must contain "SELECT artist, title"')
    if 'LIMIT ' not in s:
        raise Exception('SQL must contain "LIMIT "')

    track_names = execute_sql_get_list(p_name, s)

    if SPOTIFY_ENABLE:
        playlist_id = playlist_exists(p_name)

        if playlist_id is None:
            playlist_id = playlist_create(p_name)
            # If the playlist did not exist then always add/replace tracks
            replace_tracks = 1

        if replace_tracks:
            playlist_replace_tracks_name(playlist_id, track_names)

    return track_names


def year_tops_tracks():
    years = database_get_years()

    for year in years:
        p_name = f"Top 50 {year[0]}"
        tracks = execute_sql_get_list(
            p_name,
            f"SELECT artist, title, count(*) "
            f"FROM lastfm_scrobbles "
            f"WHERE strftime('%Y', timestamp, 'unixepoch') == '{year[0]}' "
            f"GROUP BY artist, title "
            f"ORDER BY count(*) DESC "
            f"LIMIT 50")
        create_playlist_and_add_tracks(p_name, tracks)


def year_tops_artists():
    years = database_get_years()

    for year in years:
        p_name = f"Top 50 {year[0]} artists"
        artists = execute_sql_get_list(
            p_name,
            f"SELECT artist, count(*) "
            f"FROM lastfm_scrobbles "
            f"WHERE strftime('%Y', timestamp, 'unixepoch') == '{year[0]}' "
            f"GROUP BY artist "
            f"ORDER BY count(*) DESC "
            f"LIMIT 50")

        if SPOTIFY_ENABLE:
            playlist_id = playlist_exists(p_name)

            if playlist_id is None:
                playlist_id = playlist_create(p_name)

                for artist in artists:
                    found_artist = spotify_get_artist(artist[0])
                    if found_artist is not None:
                        artist_uri = found_artist['uri']
                        artist_tops = spotify_get_artist_top_tracks(artist_uri)

                        if len(artist_tops) != 0:
                            playlist_add_tracks_uri(playlist_id, artist_tops)


def top50_total_artists():
    p_name = f"Top 50 total artists"
    artists = execute_sql_get_list(
        p_name,
        f"SELECT artist, count(*) "
        f"FROM lastfm_scrobbles "
        f"GROUP BY artist "
        f"ORDER BY count(*) DESC "
        f"LIMIT 50")

    if SPOTIFY_ENABLE:
        playlist_id = playlist_exists(p_name)
        if playlist_id is None:
            playlist_id = playlist_create(p_name)

        playlist_replace_tracks_uri(playlist_id, [])

        for artist in artists:
            found_artist = spotify_get_artist(artist[0])
            if found_artist is not None:
                artist_uri = found_artist['uri']
                artist_tops = spotify_get_artist_top_tracks(artist_uri)

                if len(artist_tops) != 0:
                    playlist_add_tracks_uri(playlist_id, artist_tops)


def year_discovery_artists():
    artist_total_list = []

    years = database_get_years()
    years.reverse()

    for year in years:
        p_name = f"Year discovery {year[0]} artists"
        artists = execute_sql_get_list(
            p_name,
            f"SELECT artist, count(*) "
            f"FROM lastfm_scrobbles "
            f"WHERE strftime('%Y', timestamp, 'unixepoch') == '{year[0]}' "
            f"GROUP BY artist "
            f"ORDER BY count(*) DESC")

        if SPOTIFY_ENABLE:
            playlist_id = playlist_exists(p_name)

            if playlist_id is None:
                playlist_id = playlist_create(p_name)

                artist_count = 0

                for artist in artists:
                    if artist[0] not in artist_total_list and artist_count < 25:
                        artist_count += 1
                        found_artist = spotify_get_artist(artist[0])
                        if found_artist is not None:
                            artist_uri = found_artist['uri']
                            artist_tops = spotify_get_artist_top_tracks(artist_uri)

                            if len(artist_tops) != 0:
                                playlist_add_tracks_uri(playlist_id, artist_tops)

                    # Add all artists to the list
                    artist_total_list.append(artist[0])


def year_discovery_tracks():
    tracks_total_list = []

    years = database_get_years()
    years.reverse()

    for year in years:
        p_name = f"Year discovery {year[0]} tracks"
        tracks = execute_sql_get_list(
            p_name,
            f"SELECT artist, title, count(*) "
            f"FROM lastfm_scrobbles "
            f"WHERE strftime('%Y', timestamp, 'unixepoch') == '{year[0]}' "
            f"GROUP BY artist, title "
            f"ORDER BY count(*) DESC")

        if SPOTIFY_ENABLE:
            playlist_id = playlist_exists(p_name)

            if playlist_id is None:
                playlist_id = playlist_create(p_name)

                list_of_track_uri = []
                track_count = 0

                for track in tracks:
                    track_str = f"{track[0]}{track[1]}"
                    if track_str not in tracks_total_list and track_count < 25:
                        track_count += 1
                        found_track = spotify_find_track(track[0], track[1])

                        if found_track is not None:
                            list_of_track_uri.append(found_track['uri'])

                    # add all tracks to the list
                    tracks_total_list.append(track_str)

                if len(list_of_track_uri) != 0:
                    playlist_add_tracks_uri(playlist_id, list_of_track_uri)


def old_favorites():
    years = database_get_years()
    for i in range(1, len(years)):
        p_name = f"Old favorites - {i} years"
        tracks = execute_sql_get_list(
            p_name,
            f"SELECT artist, title, count(*) "
            f"FROM lastfm_scrobbles "
            f"GROUP BY artist, title "
            f"HAVING strftime('%Y-%m-%d', max(timestamp), 'unixepoch') < date(strftime('%Y-%m-%d','now'), '-{i} year') "
            f"ORDER BY count(*) DESC "
            f"LIMIT 0,50")
        create_playlist_and_add_tracks(p_name, tracks)


def create_recommended(t):
    print(f'create_recommended: {t}')

    p_name = ''
    sql_name = ''
    s = ''

    if t == 'weekly':
        last_week = prev_week_range()
        dt = datetime.fromisoformat(last_week[0])
        year = dt.year
        week_number = dt.isocalendar()[1]

        sql_name = f'{year}.{week_number} - top list'
        s = f"SELECT artist, title, count(*), " \
            f"date('now', '-13 days', 'weekday 1'), date('now', '-13 days', 'weekday 1', '+6 days') " \
            f"FROM (SELECT artist, title, timestamp " \
            f"FROM lastfm_scrobbles " \
            f"WHERE date('now', '-13 days', 'weekday 1') <= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"AND date('now', '-13 days', 'weekday 1', '+6 days') >= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"ORDER BY timestamp DESC) as last_week " \
            f"GROUP BY artist, title " \
            f"ORDER BY count(*) DESC " \
            f"LIMIT 50"

        p_name = f'{year}.{week_number} - recommended'

    elif t == 'monthly':
        last_month = prev_month_range()
        dt = datetime.fromisoformat(last_month[0])
        year = dt.year
        month = dt.strftime('%h')

        sql_name = f'{year}.{month} - top list'
        s = f"SELECT artist, title, count(*), " \
            f"date('now', 'start of month', '-1 month'), date('now','start of month', '-1 day') " \
            f"FROM (SELECT artist, title, timestamp " \
            f"FROM lastfm_scrobbles " \
            f"WHERE date('now', 'start of month', '-1 month') <= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"AND date('now','start of month', '-1 day') >= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"ORDER BY timestamp DESC) as last_month " \
            f"GROUP BY artist, title " \
            f"ORDER BY count(*) DESC " \
            f"LIMIT 50"

        p_name = f'{year}.{month} - recommended'

    elif t == 'yearly':
        now = datetime.now()
        year = now.year - 1

        sql_name = f'{year} - top list'
        s = f"SELECT artist, title, count(*), " \
            f"date('now','-1 year', 'start of year'), date('now', 'start of year', '-1 day') " \
            f"FROM (SELECT artist, title, timestamp " \
            f"FROM lastfm_scrobbles " \
            f"WHERE date('now','-1 year', 'start of year') <= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"AND date('now', 'start of year', '-1 day') >= strftime('%Y-%m-%d', timestamp, 'unixepoch') " \
            f"ORDER BY timestamp DESC) as last_month " \
            f"GROUP BY artist, title " \
            f"ORDER BY count(*) DESC " \
            f"LIMIT 50"

        p_name = f'{year} - recommended'

    tracks = create_playlist_from_sql(sql_name, s, replace_tracks=0)

    if tracks:
        end_date = tracks[0][4]

        playlist_id_lastfm = playlist_exists(f"{p_name}_lastfm")

        if playlist_id_lastfm is None:
            playlist_id_lastfm = playlist_create(f"{p_name}_lastfm")

            track_names_lastfm = lastfm_get_recommended_tracks_list(tracks, end_date)
            playlist_add_tracks_name(playlist_id_lastfm, track_names_lastfm)

        if SPOTIFY_ENABLE:
            playlist_id_spotify = playlist_exists(f"{p_name}_spotify")

            if playlist_id_spotify is None:
                playlist_id_spotify = playlist_create(f"{p_name}_spotify")

                track_names_spotify = spotify_get_recommended_tracks_list(tracks, end_date)
                playlist_add_tracks_uri(playlist_id_spotify, track_names_spotify)


def my_hit_wonders(number_of_hits):
    sql = "SELECT artist, count(artist) as total_tracks_of_artist, sum(scrobbles) as total_scrobbles, " \
          "sum(scrobbles)/count(artist) as ratio " \
          "FROM (SELECT artist, title, count(*) as scrobbles FROM lastfm_scrobbles " \
          "GROUP BY artist, title ORDER BY count(*) DESC) as top " \
          "GROUP BY artist " \
          "ORDER BY ratio ASC"
    sql_rows = execute_sql_get_list(f'my_{number_of_hits}_hit_wonders', sql)

    list_of_wonder_artists = []

    for row in sql_rows:
        if row[1] == number_of_hits and row[3] > 9:
            list_of_wonder_artists.insert(0, row[0])

    if SPOTIFY_ENABLE:
        playlist_id = playlist_exists(f'My {number_of_hits} Hit Wonders')

        if playlist_id is None:
            playlist_id = playlist_create(f'My {number_of_hits} Hit Wonders')

            for artist in list_of_wonder_artists:
                tracks = database_find_tracks_from_artist(artist)
                playlist_add_tracks_name(playlist_id, tracks)

# def recommended_playlist(list):
#    pass


# #################### Flourish ###############

def line_chart_top_artists():
    sql_years = database_get_years()
    sql_artists = database_get_top_artists(250)

    years = []
    artists = []

    for year in sql_years:
        years.append(year[0])

    for artist in sql_artists:
        artists.append(artist[0])

    years.reverse()

    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

    filename = f"./CSV/flourish_artists.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', skipinitialspace=True)

        first_row = ['Artist']

        for year in years:
            for month in months:
                first_row.append(f"{year}-{month}")

        csv_writer.writerow(first_row)

        count = execute_sql_get_list('line_chart_artist',
            "SELECT artist, "
            "strftime('%Y', timestamp, 'unixepoch'), "
            "strftime('%m', timestamp, 'unixepoch'), "
            "count(*) "
            "FROM lastfm_scrobbles "
            "GROUP BY artist, strftime('%Y', timestamp, 'unixepoch'), strftime('%m', timestamp, 'unixepoch') "
            "ORDER BY artist")

        for artist in artists:
            row = [f'"{artist}"']
            total_count = 0
            for year in years:
                for month in months:
                    for c in count:
                        if c[0] == artist and c[1] == year and c[2] == month:
                            total_count += int(c[3])
                            row.append(total_count)
                            break
                    else:
                        row.append(total_count)
            csv_writer.writerow(row)
            print(artist)
    return


def line_chart_top_tracks():
    sql_years = database_get_years()
    sql_tracks = database_get_top_tracks(250)

    years = []
    tracks = []

    for year in sql_years:
        years.append(year[0])

    for track in sql_tracks:
        tracks.append(f'{track[0]} - {track[1]}')

    years.reverse()

    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

    filename = f"./CSV/flourish_tracks.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', skipinitialspace=True)

        first_row = ['Track']

        for year in years:
            for month in months:
                first_row.append(f"{year}-{month}")

        csv_writer.writerow(first_row)

        count = execute_sql_get_list('line_chart_tracks',
            "SELECT artist, title, "
            "strftime('%Y', timestamp, 'unixepoch'), "
            "strftime('%m', timestamp, 'unixepoch'), "
            "count(*) "
            "FROM lastfm_scrobbles "
            "GROUP BY artist, title, strftime('%Y', timestamp, 'unixepoch'), strftime('%m', timestamp, 'unixepoch') "
            "ORDER BY artist, title")

        for track in tracks:
            row = [f'"{track}"']
            total_count = 0
            for year in years:
                for month in months:
                    for c in count:
                        if f'{c[0]} - {c[1]}' == track and c[2] == year and c[3] == month:
                            total_count += int(c[4])
                            row.append(total_count)
                            break
                    else:
                        row.append(total_count)
            csv_writer.writerow(row)
            print(track)
    return


def line_chart_top_albums():
    sql_years = database_get_years()
    sql_album = database_get_top_albums(250)

    years = []
    albums = []

    for year in sql_years:
        years.append(year[0])

    for album in sql_album:
        albums.append(f'{album[0]}')

    years.reverse()

    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

    filename = f"./CSV/flourish_albums.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', skipinitialspace=True)

        first_row = ['Album']

        for year in years:
            for month in months:
                first_row.append(f"{year}-{month}")

        csv_writer.writerow(first_row)

        count = execute_sql_get_list('line_chart_albums',
            "SELECT album, "
            "strftime('%Y', timestamp, 'unixepoch'), "
            "strftime('%m', timestamp, 'unixepoch'), "
            "count(*) "
            "FROM lastfm_scrobbles "
            "WHERE album IS NOT NULL "
            "GROUP BY album, strftime('%Y', timestamp, 'unixepoch'), strftime('%m', timestamp, 'unixepoch') "
            "ORDER BY album")

        for album in albums:
            row = [f'"{album}"']
            total_count = 0
            for year in years:
                for month in months:
                    for c in count:
                        if f'{c[0]}' == album and c[1] == year and c[2] == month:
                            total_count += int(c[3])
                            row.append(total_count)
                            break
                    else:
                        row.append(total_count)
            csv_writer.writerow(row)
            print(album)
    return

# ################# STATS #####################


def get_stats():
    artist_every_year()


def artist_every_year():
    sql_years = database_get_years()
    sql_artists = database_get_top_artists()

    years = []
    artists = []

    for year in sql_years:
        years.append(year[0])

    for artist in sql_artists:
        artists.append(artist[0])

    years.reverse()

    filename = f"./CSV/artist_every_year.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', skipinitialspace=True)

        first_row = ['Artist']

        for year in years:
            first_row.append(f"{year}")
        first_row.append('"total number of played years"')

        csv_writer.writerow(first_row)

        count = execute_sql_get_list('every_year_artist',
                                     "SELECT artist, "
                                     "strftime('%Y', timestamp, 'unixepoch'), "
                                     "count(*) "
                                     "FROM lastfm_scrobbles "
                                     "GROUP BY artist, strftime('%Y', timestamp, 'unixepoch') "
                                     "ORDER BY artist")

        for artist in artists:
            row = [f'"{artist}"']
            total_count = 0
            for year in years:
                for c in count:
                    if c[0] == artist and c[1] == year:
                        row.append(c[2])
                        total_count += 1
                        break
                else:
                    row.append(0)
            row.append(total_count)
            csv_writer.writerow(row)
    return

# ################# MAIN ######################


if __name__ == "__main__":
    try:
        action = sys.argv[1]

        if SPOTIFY_ENABLE:
            playlist_get_all()

        if action == 'get_stats':
            get_stats()
        if action == 'line_chart_top_albums':
            line_chart_top_albums()
        if action == 'line_chart_top_tracks':
            line_chart_top_tracks()
        elif action == 'line_chart_top_artists':
            line_chart_top_artists()
        elif action == 'my_hit_wonders':
            number_of_hits = int(sys.argv[2])
            my_hit_wonders(number_of_hits)
        elif action == 'get_all_scrobbles':
            number_of_scrobbles = int(sys.argv[2])
            get_all_scrobbles(number_of_scrobbles)
        elif action == 'update_scrobbles':
            update_database(1000)
        elif action == 'update_durations':
            limit = int(sys.argv[2])
            update_durations(limit)
        elif action == 'year_tops_tracks':
            year_tops_tracks()
        elif action == 'year_tops_artists':
            year_tops_artists()
        elif action == 'top50_total_artists':
            top50_total_artists()
        elif action == 'year_discovery_artists':
            year_discovery_artists()
        elif action == 'year_discovery_tracks':
            year_discovery_tracks()
        elif action == 'old_favorites':
            old_favorites()
        elif action == 'recommended_weekly':
            create_recommended('weekly')
        elif action == 'recommended_monthly':
            create_recommended('monthly')
        elif action == 'recommended_yearly':
            create_recommended('yearly')
        elif action == 'sql':
            # the sql must have SELECT artist, title
            playlist_name = str(sys.argv[2])
            sql = str(sys.argv[3])

            create_playlist_from_sql(playlist_name, sql)
        # elif action == 'follow_artists':
            # get arg with X scrobble
            # follow all artists on Spotify over X scrobbles
        # elif action == 'sync_loved':
            # sync loved with database and update the playlist
        # elif action == 'top_artists':
            # create playlist with top5 scrobbled tracks from top artists
            # create playlist with top5 spotify tracks from top artists
        # elif action == 'year':
            # Possible to create playlist from years from Spotify

        DATABASE.close()
    except Exception as e:
        print(f"\n\n{action} had an exception:{e}\n\n")
        print(traceback.format_exc())
