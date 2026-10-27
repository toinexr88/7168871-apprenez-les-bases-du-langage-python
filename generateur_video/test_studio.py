import subprocess

import pytest
from PIL import Image

import app_web
import main
import studio

PETIT = dict(largeur=64, hauteur=48, images_par_seconde=10, duree_photo=1.0, duree_fondu=0.3)


def duree_video(chemin):
    sortie = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames,width,height", "-of", "csv=p=0", str(chemin)],
        capture_output=True, text=True, check=True,
    )
    largeur, hauteur, images = sortie.stdout.strip().split(",")
    return int(largeur), int(hauteur), int(images)


def test_nombre_images_correspond_au_calcul(tmp_path):
    photos = studio.creer_photos_demo(tmp_path / "photos", nombre=3)
    reglages = studio.Reglages(**PETIT, titre="Titre", duree_titre=1.0)
    images = list(studio.generer_images(photos, reglages))
    assert len(images) == studio.nombre_total_images(3, reglages)
    assert all(image.size == (64, 48) for image in images)


def test_creer_video_produit_un_mp4(tmp_path):
    photos = studio.creer_photos_demo(tmp_path / "photos", nombre=2)
    reglages = studio.Reglages(**PETIT, legendes=["Un", "Deux"])
    sortie = studio.creer_video(photos, tmp_path / "video.mp4", reglages)
    assert duree_video(sortie) == (64, 48, studio.nombre_total_images(2, reglages))


def test_ken_burns_sans_zoom_garde_la_photo(tmp_path):
    reglages = studio.Reglages(**{**PETIT, "zoom": 1.0})
    photo = Image.new("RGB", (64, 48), (10, 20, 30))
    image = studio.image_ken_burns(photo, 0.5, 0, reglages)
    assert image.getpixel((32, 24)) == (10, 20, 30)


@pytest.mark.parametrize("modif", [{"largeur": 63}, {"duree_fondu": 2.0}, {"zoom": 0.5}])
def test_reglages_invalides(modif):
    with pytest.raises(ValueError):
        studio.Reglages(**{**PETIT, **modif}).verifier()


def test_lister_photos_ignore_les_autres_fichiers(tmp_path):
    studio.creer_photos_demo(tmp_path, nombre=2)
    (tmp_path / "notes.txt").write_text("pas une photo")
    assert [p.name for p in studio.lister_photos(tmp_path)] == ["demo_01.png", "demo_02.png"]


def test_ligne_de_commande_demo(tmp_path):
    sortie = tmp_path / "demo.mp4"
    code = main.main(["--demo", "-o", str(sortie), "--resolution", "64x48", "--ips", "5"])
    assert code == 0 and sortie.is_file()


def test_formulaire_web(tmp_path, monkeypatch):
    monkeypatch.setattr(app_web, "DOSSIER_TRAVAIL", tmp_path)
    monkeypatch.setitem(app_web.RESOLUTIONS, "720p", (64, 48))
    photo = tmp_path / "p.png"
    Image.new("RGB", (80, 60), "red").save(photo)
    limite = "XXLIMITEXX"
    corps = (
        f"--{limite}\r\nContent-Disposition: form-data; name=\"titre\"\r\n\r\nSalut\r\n"
        f"--{limite}\r\nContent-Disposition: form-data; name=\"photos\"; filename=\"p.png\"\r\n"
        "Content-Type: image/png\r\n\r\n"
    ).encode() + photo.read_bytes() + f"\r\n--{limite}--\r\n".encode()
    champs, fichiers = app_web.lire_formulaire(f"multipart/form-data; boundary={limite}", corps)
    assert champs["titre"] == "Salut"
    assert fichiers["photos"][0][1] == photo.read_bytes()
    identifiant = app_web.generer_depuis_formulaire(champs, fichiers)
    assert (tmp_path / identifiant / "video.mp4").is_file()
