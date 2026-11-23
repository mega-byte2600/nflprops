"""Tests for the HTTP backend (props_api.py)."""
import hashlib
import hmac
import json
import threading

from ios.backend import props_api as api


def _server():
    import test_snapshot_server as tss
    df = tss._small_stats()
    srv = api._ConfigServer(("127.0.0.1", 0), api.SnapshotHandler)
    srv.stats = df
    srv.n = 1000
    srv.ci = 0.95
    srv.secret = "test-secret"
    return srv


def _start():
    srv = _server()
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]


def test_health_endpoint():
    srv, port = _start()
    try:
        import urllib.request
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/health").read()
        assert json.loads(body) == {"ok": True}
    finally:
        srv.shutdown(); srv.server_close()


def test_snapshot_signed_and_validates():
    srv, port = _start()
    try:
        import urllib.request
        # use specs that resolve in the synthetic frame (WR0-WR5)
        srv.specs = [(f"WR{i}", "receiving_yards", 60.0) for i in range(6)]
        env = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}/snapshot").read())
        assert env["signature"]
        # verify the HMAC over the payload (as the iOS client would)
        body = json.dumps(env["payload"], sort_keys=True).encode()
        want = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        assert want == env["signature"]
        assert len(env["payload"]["props"]) > 0
        assert env["payload"]["honesty"]
    finally:
        srv.shutdown(); srv.server_close()


def test_unknown_path_404():
    srv, port = _start()
    try:
        import urllib.error
        import urllib.request
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope")
            assert False, "should 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown(); srv.server_close()