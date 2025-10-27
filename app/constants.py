"""Application-wide constants and defaults."""

from pathlib import Path

SCOPES = "https://www.googleapis.com/auth/drive"
CLIENT_SECRET_FILE = "credentials.json"
APPLICATION_NAME = "Drive API Python Quickstart"

DEFAULT_FOLDER_ID = ""
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VIDEOSUBFINDER_PATH = str(
    (PROJECT_ROOT / "video-app" / "VideoSubFinderWXW_intel.exe").resolve()
)
DEFAULT_THREADS = 20
