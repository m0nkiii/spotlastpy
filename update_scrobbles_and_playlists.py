import sys
import subprocess

if __name__ == "__main__":
    try:
        # Start with getting all scrobbles, paramter is the number of total scrobbles to get
        # so round it up and run
        # subprocess.call('python main.py get_all_scrobbles 1000')

        update = 0
        duration = 0
        artist_tops = 0
        random = 0
        top_total = 0
        unique = 0
        recommended = 0
        my_hit_wonders = 1

# Update

        if update:
            subprocess.call('python main.py update_scrobbles')

        if duration:
            subprocess.call('python main.py update_durations 10')

# Artist tops

        if artist_tops:
            artists = ['Wilmer X', 'Lagwagon', 'Nightwish', 'Him', 'Disturbed']

            for artist in artists:
                subprocess.call(f"python main.py sql \"My {artist}\" \"SELECT artist, title, count(*) FROM lastfm_scrobbles GROUP BY artist, title HAVING artist = '{artist}' ORDER BY count(*) DESC LIMIT 50\"")

# Random and generated new each time

        if random:
            subprocess.call("python main.py sql \"My 2 rand\" \"SELECT artist, title, count(*)FROM lastfm_scrobbles GROUP BY artist, title HAVING count(*) > 1 AND count(*) < 5 ORDER BY Random() LIMIT 50\"")
            subprocess.call("python main.py sql \"My 5 rand\" \"SELECT artist, title, count(*) FROM lastfm_scrobbles GROUP BY artist, title HAVING count(*) > 4 AND count(*) < 10 ORDER BY Random() LIMIT 50\"")
            subprocess.call("python main.py sql \"My 10 rand\" \"SELECT artist, title, count(*) FROM lastfm_scrobbles GROUP BY artist, title HAVING count(*) > 9 AND count(*) < 50 ORDER BY Random() LIMIT 50\"")
            subprocess.call("python main.py sql \"My 50 rand\" \"SELECT artist, title, count(*) FROM lastfm_scrobbles GROUP BY artist, title HAVING count(*) > 49 ORDER BY Random() LIMIT 50\"")

# Updated Playlists

        if top_total:
            subprocess.call("python main.py sql \"Top 50 total\" \"SELECT artist, title, count(*) FROM lastfm_scrobbles GROUP BY artist, title ORDER BY count(*) DESC LIMIT 50\"")
            subprocess.call("python main.py top50_total_artists")

# Unique

        if unique:
            subprocess.call('python main.py year_tops_tracks')
            subprocess.call('python main.py year_tops_artists')
            subprocess.call("python main.py year_discovery_artists")
            subprocess.call("python main.py year_discovery_tracks")
            subprocess.call("python main.py old_favorites")

# Recommended

        if recommended:
            subprocess.call("python main.py recommended_weekly")
            subprocess.call("python main.py recommended_monthly")
            subprocess.call("python main.py recommended_yearly")

# My hit wonders

        if my_hit_wonders:
            subprocess.call("python main.py my_hit_wonders 1")
            subprocess.call("python main.py my_hit_wonders 2")
            subprocess.call("python main.py my_hit_wonders 3")
            subprocess.call("python main.py my_hit_wonders 4")
            subprocess.call("python main.py my_hit_wonders 5")

    except Exception as e:
        print(f"Exception:{e}\n")
