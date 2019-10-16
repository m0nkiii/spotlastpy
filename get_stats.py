import sys
import subprocess

if __name__ == "__main__":
    try:
        subprocess.call("python main.py get_stats")

    except Exception as e:
        print(f"Exception:{e}\n")
