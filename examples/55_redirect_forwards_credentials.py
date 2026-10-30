"""urllib.request forwards Authorization and Cookie headers to wherever a redirect points."""

import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

received = {}


class OtherHost(BaseHTTPRequestHandler):
    def do_GET(self):
        received["Authorization"] = self.headers.get("Authorization")
        received["Cookie"] = self.headers.get("Cookie")
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


other = HTTPServer(("127.0.0.1", 0), OtherHost)
threading.Thread(target=other.serve_forever, daemon=True).start()


class Api(BaseHTTPRequestHandler):
    def do_GET(self):
        # Redirect to a different host ("localhost" vs "127.0.0.1") and port.
        self.send_response(302)
        self.send_header("Location", f"http://localhost:{other.server_port}/")
        self.end_headers()

    def log_message(self, *args):
        pass


api = HTTPServer(("127.0.0.1", 0), Api)
threading.Thread(target=api.serve_forever, daemon=True).start()
headers = {"Authorization": "Bearer api-token", "Cookie": "session=abc123"}

# The trap
urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{api.server_port}/", headers=headers)).read()
print(received)  # {'Authorization': 'Bearer api-token', 'Cookie': 'session=abc123'}
assert received == headers


# The fix: drop credentials when a redirect changes scheme, host or port.
class SameOriginCredentials(urllib.request.HTTPRedirectHandler):
    SENSITIVE = {"authorization", "cookie", "proxy-authorization"}

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        new = super().redirect_request(req, fp, code, msg, hdrs, newurl)
        old, target = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if new is not None and (old.scheme, old.netloc) != (target.scheme, target.netloc):
            for name in list(new.headers):
                if name.lower() in self.SENSITIVE:
                    del new.headers[name]
        return new


received.clear()
opener = urllib.request.build_opener(SameOriginCredentials)
opener.open(urllib.request.Request(f"http://127.0.0.1:{api.server_port}/", headers=headers)).read()
assert received == {"Authorization": None, "Cookie": None}

api.shutdown()
other.shutdown()
