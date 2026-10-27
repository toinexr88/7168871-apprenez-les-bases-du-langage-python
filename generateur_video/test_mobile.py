import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app_web


@pytest.fixture
def serveur(tmp_path, monkeypatch):
    monkeypatch.setattr(app_web, "DOSSIER_TRAVAIL", tmp_path)
    (tmp_path / "abc123").mkdir()
    (tmp_path / "abc123" / "video.mp4").write_bytes(bytes(range(256)) * 4)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app_web.Gestionnaire)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def lire(url, entetes=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=entetes or {})) as r:
        return r.status, dict(r.headers), r.read()


def test_pages_adaptees_au_mobile(serveur):
    for chemin in ("/", "/diaporama", "/montage"):
        _, _, corps = lire(serveur + chemin)
        assert b"viewport-fit=cover" in corps and b"/manifest.json" in corps


def test_manifeste_et_icones(serveur):
    _, _, corps = lire(serveur + "/manifest.json")
    assert json.loads(corps)["display"] == "standalone"
    _, entetes, png = lire(serveur + "/icone.png")
    assert entetes["Content-Type"] == "image/png" and png[:4] == b"\x89PNG"


def test_video_par_plages_pour_iphone(serveur):
    statut, entetes, corps = lire(serveur + "/video/abc123.mp4", {"Range": "bytes=10-19"})
    assert statut == 206
    assert entetes["Content-Range"] == "bytes 10-19/1024"
    assert corps == bytes(range(10, 20))
    statut, entetes, corps = lire(serveur + "/video/abc123.mp4")
    assert statut == 200 and entetes["Accept-Ranges"] == "bytes" and len(corps) == 1024
