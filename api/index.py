import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "web"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from app import app  # noqa: E402,F401  (Flask WSGI app from web/app.py)
