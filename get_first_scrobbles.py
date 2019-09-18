import sys
import subprocess

if __name__ == "__main__":
    try:
        # Start with getting all scrobbles, paramter is the number of total scrobbles to get so round it up and run
        subprocess.call('python main.py get_all_scrobbles 30000')

    except Exception as e:
        print(f"Exception:{e}\n")
