import sys
import subprocess

if __name__ == "__main__":
    try:
        subprocess.call("python main.py line_chart_top_tracks")
        subprocess.call("python main.py line_chart_top_artists")
        subprocess.call("python main.py line_chart_top_albums")

    except Exception as e:
        print(f"Exception:{e}\n")
