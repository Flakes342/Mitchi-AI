import subprocess
import pyautogui
import urllib
import time
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-playback-state,user-modify-playback-state"
))


def open_app(app_name: str, query: str = ""):
    app_name = app_name.lower().strip()
    query = query.strip()
    
    commands = {
        "spotify": "spotify",
        "vscode": "code",
        "youtube": "firefox https://youtube.com",
        "netflix": "firefox https://netflix.com",
        "chatgpt": "firefox https://chatgpt.com",
        "linkedin": "firefox https://linkedin.com",
        "github": "firefox https://github.com/Flakes342",
        "chrome": "google-chrome",
    }
    cmd = commands.get(app_name.lower())

    if not app_name:
        return "No app name provided. Please specify an app to open."

    elif app_name == 'terminal':
        # Special case for terminal, use hotkey
        pyautogui.hotkey("alt", "ctrl", "t")
        return "Opening terminal..."
    
    elif app_name == "spotify":
        try:
            subprocess.Popen(cmd.split())
            return f"Opening {app_name}..."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    elif app_name == "youtube":
        if query:
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
            cmd = f"firefox {search_url}"
            subprocess.Popen(cmd.split())
            time.sleep(10)
            pyautogui.click(613, 297)
            return f"Opened YouTube and searched: {query}"

    elif cmd:
        try:
            subprocess.Popen(cmd.split())
            return f"Opening {app_name}..."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"
    return f"App '{app_name}' not recognized."
