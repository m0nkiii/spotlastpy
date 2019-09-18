import os
import sys
import pylast

def track_and_timestamp(track):
    return f"{track.playback_date}\t{track.track}"

def print_track(track):
    print(track_and_timestamp(track))
