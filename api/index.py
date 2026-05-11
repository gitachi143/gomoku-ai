import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "web"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app import app  # noqa: E402,F401  (Flask WSGI app from web/app.py)
