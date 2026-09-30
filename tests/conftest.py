import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
os.environ.setdefault("APP_DB_PATH", tempfile.mktemp(suffix=".db"))
