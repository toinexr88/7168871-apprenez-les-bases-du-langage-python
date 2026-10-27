import subprocess

import pytest

import app_web
import montage


def creer_clip(chemin, duree, taille="320x240", son=True):
    commande = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={taille}:rate=24:d={duree}"]
    if son:
        commande += ["-f", "lavfi", "-i", f"sine=d={duree}", "-shortest"]
    subprocess.run(commande + ["-pix_fmt", "yuv420p", str(chemin)], check=True)
    return chemin


def infos(chemin):
    sortie = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", str(chemin)], capture_output=True, text=True, check=True,
    ).stdout
    import json
    donnees = json.loads(sortie)
    video = next(f for f in donnees["streams"] if f["codec_type"] == "video")
    types = {f["codec_type"] for f in donnees["streams"]}
    return float(donnees["format"]["duration"]), (video["width"], video["height"]), "audio" in types


@pytest.fixture
def clips(tmp_path):
    return [
        creer_clip(tmp_path / "a.mp4", 2),
        creer_clip(tmp_path / "b.mp4", 1.5, "240x400", son=False),
        creer_clip(tmp_path / "c.mp4", 1),
    ]


def test_assemblage_bout_a_bout(clips, tmp_path):
    duree, taille, son = infos(montage.assembler(clips, tmp_path / "m.mp4", "1:1"))
    assert duree == pytest.approx(4.5, abs=0.1)
    assert taille == (1080, 1080) and son


def test_assemblage_avec_fondu(clips, tmp_path):
    duree, _, _ = infos(montage.assembler(clips, tmp_path / "m.mp4", fondu=0.5))
    assert duree == pytest.approx(3.5, abs=0.1)


def test_assemblage_sans_son(clips, tmp_path):
    duree, taille, son = infos(montage.assembler([clips[1], clips[1]], tmp_path / "m.mp4"))
    assert duree == pytest.approx(3, abs=0.1) and taille == (1280, 720) and not son


def test_fondu_trop_long(clips, tmp_path):
    with pytest.raises(ValueError, match="fondu"):
        montage.assembler(clips, tmp_path / "m.mp4", fondu=1.5)


def test_fichier_non_video(tmp_path):
    faux = tmp_path / "x.mp4"
    faux.write_text("pas une vidéo")
    with pytest.raises(ValueError, match="pas une vidéo lisible"):
        montage.assembler([faux], tmp_path / "m.mp4")


def test_montage_web(clips, tmp_path, monkeypatch):
    dossier = tmp_path / "travail"
    monkeypatch.setattr(app_web, "DOSSIER_TRAVAIL", dossier)
    (dossier / "abc123").mkdir(parents=True)
    (dossier / "abc123" / "video.mp4").write_bytes(clips[0].read_bytes())
    app_web.nommer(dossier / "abc123", "Agnes : plage")
    champs = {"ordre": "fichier:0\nserveur:abc123\nfichier:1", "format": "16:9", "fondu": "0"}
    fichiers = {"clips": [("b.mp4", clips[1].read_bytes()), ("c.mp4", clips[2].read_bytes())]}
    identifiant = app_web.assembler_montage(champs, fichiers)
    duree, _, _ = infos(dossier / identifiant / "video.mp4")
    assert duree == pytest.approx(4.5, abs=0.1)
    assert [v["nom"] for v in app_web.lister_videos()] == ["Montage : 3 segment(s)", "Agnes : plage"]


@pytest.mark.parametrize("ordre", ["serveur:../x", "fichier:5", "inconnu:1", ""])
def test_montage_web_refuse_segment_invalide(ordre, tmp_path, monkeypatch):
    monkeypatch.setattr(app_web, "DOSSIER_TRAVAIL", tmp_path)
    with pytest.raises(ValueError):
        app_web.assembler_montage({"ordre": ordre}, {})
