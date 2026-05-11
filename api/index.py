import sys
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "web"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from app import app  # noqa: E402,F401  (Flask WSGI app from web/app.py)
except Exception:
    _err = traceback.format_exc()
    try:
        _files = sorted(str(p.relative_to(_ROOT)) for p in _ROOT.rglob("*") if p.is_file())
    except Exception:
        _files = ["<unable to list>"]
    _listing = "\n".join(_files[:300])

    from flask import Flask  # type: ignore
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _debug(path):
        sys_path = "\n".join(sys.path)
        return (
            "<pre style='font-family:monospace;white-space:pre-wrap'>"
            f"IMPORT FAILED\n\n{_err}\n\n"
            f"--- sys.path ---\n{sys_path}\n\n"
            f"--- _ROOT ({_ROOT}) contents (first 300) ---\n{_listing}"
            "</pre>",
            500,
        )
