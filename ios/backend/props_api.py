"""HTTP endpoint that serves the signed prop snapshot (the app's live backend).

Wraps the same snapshot builder as snapshot_server.py behind a real HTTP GET,
so the iOS app (or any client) can fetch the signed JSON live instead of only
reading a bundled asset. The iPhone still holds NO odds key and does no heavy
compute - the server prices, signs, and serves.

Honest framing enforced here too: the snapshot carries the distribution + CI
and the explicit no-guaranteed-edge statement; this endpoint never reports a
money edge.

Uses http.server (stdlib) - no framework dependency, deployable anywhere.
Run:  venv/bin/python ios/backend/props_api.py --stats cache/player_stats.csv \
          --port 8080 --sign-secret "$SNITCH_SECRET"
Fetch: GET /snapshot   -> signed JSON
        GET /health    -> {"ok": true}
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pandas as pd

from nflprops import load_stats

# sibling import that works both when run as a script (ios/backend/) and when
# imported from the test suite
try:
    from .snapshot_server import _hmac_hex, build_snapshot
except ImportError:  # pragma: no cover - run directly as a script
    from snapshot_server import _hmac_hex, build_snapshot


class _ConfigServer(ThreadingHTTPServer):
    """ThreadingHTTPServer carrying the app's runtime config (typed)."""
    stats: pd.DataFrame
    n: int = 15000
    ci: float = 0.95
    secret: str = ""
    specs: list | None = None   # optional (player, stat, line) override


class SnapshotHandler(BaseHTTPRequestHandler):
    server_version = "PropDeskBackend/0.1"

    def log_message(self, format: str, *args):  # suppress default stderr spam
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, json.dumps({"ok": True}).encode())
            return
        if path != "/snapshot":
            self._send(404, json.dumps({"error": "not found"}).encode())
            return
        try:
            specs = getattr(self.server, "specs", None)
            if specs:
                snap = build_snapshot(self.server.stats, specs=specs,
                                      n=self.server.n, ci=self.server.ci)
            else:
                snap = build_snapshot(self.server.stats,
                                      n=self.server.n, ci=self.server.ci)
            body = json.dumps(snap, sort_keys=True).encode()
            sig = _hmac_hex(body, self.server.secret) if self.server.secret else None
            envelope = json.dumps({"signature": sig, "payload": snap}).encode()
            self._send(200, envelope)
        except Exception as exc:  # noqa: BLE001 - must never leak internals to HTTP client
            self._send(500, json.dumps({"error": "internal"}).encode())
            print(f"[props_api] snapshot error: {exc!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--sign-secret", default=os.environ.get("SNITCH_SECRET", ""))
    ap.add_argument("--ci", type=float, default=0.95)
    ap.add_argument("--n", type=int, default=15000)
    args = ap.parse_args()

    print(f"loading stats from {args.stats} ...")
    df = load_stats(args.stats)

    server = _ConfigServer((args.host, args.port), SnapshotHandler)
    server.stats = df          # cheap: snapshot priced on demand (batch precompute
    server.n = args.n          # would be a background job re-uploading a signed file)
    server.ci = args.ci
    server.secret = args.sign_secret
    print(f"PropDesk backend on http://{args.host}:{args.port}")
    print(f"  GET /snapshot  (signed={'yes' if args.sign_secret else 'NO - set --sign-secret'})")
    print("  GET /health")
    print(f"  pricing n={args.n}, ci={args.ci}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.server_close()


if __name__ == "__main__":
    main()