import logging
from pathlib import Path


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "albumcropstudio.log"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    encoding="utf-8",
    format=(
        "%(asctime)s\n"
        "%(levelname)s\n"
        "%(message)s\n"
    ),
)

def get_logger():
    return logging.getLogger("AlbumCropStudio")