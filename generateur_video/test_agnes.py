import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PIL import Image

import agnes
import app_web


def photo_png(couleur="red", taille=(300, 200)):
    tampon = io.BytesIO()
    Image.new("RGB", taille, couleur).save(tampon, "PNG")
    return tampon.getvalue()


@pytest.fixture
def faux_agnes(monkeypatch):
    """Serveur local qui imite l'API d'Agnes."""
    etat = {"requetes": [], "consultations": 0, "echec": False}

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def repondre(self, code, donnees, type_contenu="application/json"):
            corps = donnees if isinstance(donnees, bytes) else json.dumps(donnees).encode()
            self.send_response(code)
            self.send_header("Content-Type", type_contenu)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_POST(self):
            if self.headers["Authorization"] != "Bearer bonne-cle":
                return self.repondre(401, {"error": "invalid api key"})
            corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            etat["requetes"].append(corps)
            self.repondre(200, {"task_id": "task_1", "video_id": "video_1", "status": "queued"})

        def do_GET(self):
            if self.path == "/fichier.mp4":
                return self.repondre(200, b"FAUSSE-VIDEO", "video/mp4")
            assert self.path == "/agnesapi?video_id=video_1&model_name=agnes-video-2.5-flash"
            etat["consultations"] += 1
            if etat["echec"]:
                return self.repondre(200, {"status": "failed", "error": "contenu refusé"})
            if etat["consultations"] < 2:
                return self.repondre(200, {"status": "in_progress", "progress": 40})
            adresse = f"http://127.0.0.1:{serveur.server_port}/fichier.mp4"
            self.repondre(200, {"status": "completed", "progress": 100, "url": adresse})

    serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestionnaire)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    monkeypatch.setattr(agnes, "ADRESSE_API", f"http://127.0.0.1:{serveur.server_port}")
    yield etat
    serveur.shutdown()


@pytest.mark.parametrize("nombre, mode", [(0, "text"), (1, "img2video"), (2, "keyframe"), (4, "reference")])
def test_mode_automatique(nombre, mode):
    assert agnes.mode_automatique(nombre) == mode


def test_requete_une_photo():
    corps = agnes.preparer_requete("La mer bouge", [photo_png()])
    assert corps["mode"] == "img2video"
    assert Image.open(io.BytesIO(base64.b64decode(corps["first_frame"]))).size == (300, 200)


def test_requete_deux_photos_et_reduction():
    corps = agnes.preparer_requete("Transition", [photo_png(taille=(4000, 3000)), photo_png("blue")])
    assert corps["mode"] == "keyframe" and "last_frame" in corps
    assert max(Image.open(io.BytesIO(base64.b64decode(corps["first_frame"]))).size) == agnes.COTE_MAX_PHOTO


def test_requete_reference_et_flash_force_720p():
    corps = agnes.preparer_requete("Style", [photo_png()] * 3, taille="2K")
    assert corps["mode"] == "reference" and len(corps["images"]) == 3
    assert corps["size"] == "720P"


@pytest.mark.parametrize("arguments", [
    dict(prompt="", photos=[]),
    dict(prompt="ok", photos=[photo_png()] * 6),
    dict(prompt="ok", photos=[photo_png()], mode="keyframe"),
    dict(prompt="ok", photos=[photo_png()], secondes=30),
])
def test_requetes_invalides(arguments):
    with pytest.raises(ValueError):
        agnes.preparer_requete(**arguments)


def test_cle_vide_refusee():
    with pytest.raises(ValueError):
        agnes.ClientAgnes("   ")


def test_mauvaise_cle(faux_agnes):
    with pytest.raises(agnes.ErreurAgnes, match="Clé API invalide"):
        agnes.ClientAgnes("mauvaise").creer_video({"model": "x"})


def test_generation_complete(faux_agnes, tmp_path):
    client = agnes.ClientAgnes("bonne-cle")
    video_id = client.creer_video(agnes.preparer_requete("Anime", [photo_png()]))
    url = client.attendre(video_id, "agnes-video-2.5-flash", intervalle=0)
    assert agnes.telecharger(url, tmp_path / "v.mp4").read_bytes() == b"FAUSSE-VIDEO"
    assert faux_agnes["requetes"][0]["mode"] == "img2video"


def test_echec_signale(faux_agnes):
    faux_agnes["echec"] = True
    with pytest.raises(agnes.ErreurAgnes, match="contenu refusé"):
        agnes.ClientAgnes("bonne-cle").attendre("video_1", "agnes-video-2.5-flash", intervalle=0)


def test_ligne_de_commande(faux_agnes, tmp_path, monkeypatch):
    monkeypatch.setattr(agnes.time, "sleep", lambda _: None)
    photo = tmp_path / "p.png"
    photo.write_bytes(photo_png())
    sortie = tmp_path / "v.mp4"
    code = agnes.main(["--cle", "bonne-cle", "--prompt", "Anime", str(photo), "-o", str(sortie)])
    assert code == 0 and sortie.read_bytes() == b"FAUSSE-VIDEO"


def test_parcours_web(faux_agnes, tmp_path, monkeypatch):
    monkeypatch.setattr(app_web, "DOSSIER_TRAVAIL", tmp_path)
    champs = {"cle": "bonne-cle", "prompt": "Deux photos", "secondes": "6", "mode": "auto"}
    fichiers = {"photos": [("b.png", photo_png("blue")), ("a.png", photo_png("red"))]}
    travail = app_web.lancer_agnes(champs, fichiers)
    assert faux_agnes["requetes"][0]["mode"] == "keyframe"
    assert faux_agnes["requetes"][0]["seconds"] == "6"
    assert app_web.etat_agnes(travail) == {"statut": "en_cours", "progression": 40}
    assert app_web.etat_agnes(travail) == {"statut": "terminee", "video": f"/video/{travail}.mp4"}
    assert (tmp_path / travail / "video.mp4").read_bytes() == b"FAUSSE-VIDEO"
