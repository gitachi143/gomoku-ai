import importlib
import sys
import traceback
from pathlib import Path

from flask import Flask

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "web"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

# Top-level `app` so Vercel's static analyzer finds an entrypoint.
# Replaced below if importing the real web/app.py succeeds.
app = Flask(__name__)
_import_err = None

try:
    _real_mod = importlib.import_module("app")
    app = _real_mod.app
except Exception:
    _import_err = traceback.format_exc()

if _import_err is not None:
    try:
        _files = sorted(
            str(p.relative_to(_ROOT)) for p in _ROOT.rglob("*") if p.is_file()
        )
    except Exception:
        _files = ["<unable to list>"]
    _listing = "\n".join(_files[:300])
    _sys_path = "\n".join(sys.path)
    _err_text = _import_err

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _debug(path):
        return (
            "<pre style='white-space:pre-wrap;font-family:monospace'>"
            f"IMPORT FAILED\n\n{_err_text}\n\n"
            f"--- sys.path ---\n{_sys_path}\n\n"
            f"--- files under {_ROOT} (first 300) ---\n{_listing}"
            "</pre>",
            500,
        )
