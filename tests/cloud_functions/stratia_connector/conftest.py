"""Put the stratia_connector source dir on sys.path for unit tests."""
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[3] / "cloud_functions" / "stratia_connector"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))
