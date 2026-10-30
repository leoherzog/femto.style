# Serves the spike folder the way Cloudflare Pages would: /name serves name.html, and anything else
# that is not a file is a 404. Theme stylesheets answer 300 ms late, so a theme that is not applied
# before the first frame shows up in the checks.
# Run: python3 -I docs/research/spike/serve.py [port]
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
THEME_DELAY = 0.3


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = urlsplit(self.path).path
        if not Path(ROOT, path.lstrip("/")).is_file() and Path(ROOT, path.lstrip("/") + ".html").is_file():
            path += ".html"
        if not Path(ROOT, path.lstrip("/")).is_file():
            self.send_error(404)
            return None
        if path.startswith("/themes/"):
            time.sleep(THEME_DELAY)
        self.path = path
        return super().send_head()

    def end_headers(self):
        # What Cloudflare Pages sends for static files.
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        super().end_headers()


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=ROOT)).serve_forever()
