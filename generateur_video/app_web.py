"""Interface web du générateur de vidéo.

Lancement :
    python app_web.py
puis ouvrir http://localhost:8000 dans un navigateur.

Le serveur n'utilise que la bibliothèque standard de Python (http.server),
en plus de Pillow et ffmpeg utilisés par `studio.py`.
"""

import html
import tempfile
import uuid
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import studio

DOSSIER_TRAVAIL = Path(tempfile.gettempdir()) / "generateur_video"
TAILLE_MAX = 300 * 1024 * 1024  # 300 Mo d'envoi au maximum
RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080), "carre": (1080, 1080), "vertical": (1080, 1920)}

STYLE = """
* { box-sizing: border-box; min-width: 0; }
body { font-family: system-ui, sans-serif; background: #14141f; color: #eee;
       max-width: 760px; margin: 0 auto; padding: 24px 16px; }
h1 { margin-top: 0; } a { color: #9ab8ff; }
form { display: grid; gap: 14px; background: #1f1f2e; padding: 20px; border-radius: 12px; }
label { display: grid; gap: 6px; font-weight: 600; }
.ligne { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; }
input, select, textarea { font: inherit; padding: 8px; border-radius: 8px;
       border: 1px solid #444; background: #2a2a3d; color: #eee; }
small { font-weight: normal; color: #aaa; }
button { font: inherit; font-weight: 700; padding: 12px; border: 0; border-radius: 8px;
         background: #6c63ff; color: white; cursor: pointer; }
button:disabled { opacity: .6; cursor: wait; }
video { width: 100%; border-radius: 12px; background: black; }
.erreur { background: #5a1f2a; padding: 12px; border-radius: 8px; }
"""

FORMULAIRE = """
<h1>🎬 Générateur de vidéo</h1>
<p>Choisissez vos photos : elles seront assemblées en diaporama animé
(zoom lent, fondus enchaînés, titre et légendes).</p>
<form method="post" action="/generer" enctype="multipart/form-data"
      onsubmit="this.querySelector('button').disabled = true;
                this.querySelector('button').textContent = 'Génération en cours…';">
  <label>Photos <small>(dans l'ordre d'affichage, triées par nom)</small>
    <input type="file" name="photos" accept="image/*" multiple>
  </label>
  <label><span><input type="checkbox" name="demo"> Utiliser des photos de démonstration</span></label>
  <div class="ligne">
    <label>Titre <input name="titre" placeholder="Mes vacances"></label>
    <label>Sous-titre <input name="sous_titre" placeholder="Été 2026"></label>
  </div>
  <label>Légendes <small>(une par ligne, dans l'ordre des photos)</small>
    <textarea name="legendes" rows="3"></textarea>
  </label>
  <div class="ligne">
    <label>Secondes par photo <input type="number" name="duree" value="3" min="0.5" step="0.5"></label>
    <label>Fondu (s) <input type="number" name="fondu" value="0.8" min="0" step="0.1"></label>
    <label>Zoom <input type="number" name="zoom" value="1.15" min="1" max="2" step="0.05"></label>
    <label>Format
      <select name="format">
        <option value="720p">Paysage 720p</option>
        <option value="1080p">Paysage 1080p</option>
        <option value="carre">Carré (Instagram)</option>
        <option value="vertical">Vertical (Stories)</option>
      </select>
    </label>
  </div>
  <label>Musique <small>(optionnelle)</small>
    <input type="file" name="audio" accept="audio/*">
  </label>
  <button type="submit">Générer la vidéo</button>
</form>
"""


def page(contenu):
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Générateur de vidéo</title><style>{STYLE}</style></head>"
        f"<body>{contenu}</body></html>"
    ).encode("utf-8")


def lire_formulaire(entete_type, corps):
    """Découpe un envoi multipart/form-data en champs texte et fichiers."""
    message = BytesParser(policy=HTTP).parsebytes(
        f"Content-Type: {entete_type}\r\n\r\n".encode() + corps
    )
    champs, fichiers = {}, {}
    for partie in message.iter_parts():
        nom = partie.get_param("name", header="content-disposition")
        nom_fichier = partie.get_filename()
        contenu = partie.get_payload(decode=True) or b""
        if nom_fichier:
            if contenu:
                fichiers.setdefault(nom, []).append((Path(nom_fichier).name, contenu))
        else:
            champs[nom] = contenu.decode("utf-8", errors="replace")
    return champs, fichiers


def nombre(champs, nom, defaut):
    try:
        return float(champs.get(nom, "").replace(",", ".") or defaut)
    except ValueError:
        raise ValueError(f"Le champ « {nom} » doit être un nombre.")


def generer_depuis_formulaire(champs, fichiers):
    """Enregistre les fichiers envoyés puis crée la vidéo. Renvoie son identifiant."""
    identifiant = uuid.uuid4().hex[:12]
    dossier = DOSSIER_TRAVAIL / identifiant
    dossier.mkdir(parents=True)

    if champs.get("demo"):
        photos = studio.creer_photos_demo(dossier / "photos")
    else:
        photos = []
        for numero, (nom, contenu) in enumerate(sorted(fichiers.get("photos", []))):
            chemin = dossier / f"{numero:03d}_{nom}"
            chemin.write_bytes(contenu)
            photos.append(chemin)
    if not photos:
        raise ValueError("Ajoutez au moins une photo (ou cochez la démonstration).")

    audio = ""
    if fichiers.get("audio"):
        nom, contenu = fichiers["audio"][0]
        audio = dossier / f"audio_{nom}"
        audio.write_bytes(contenu)

    largeur, hauteur = RESOLUTIONS.get(champs.get("format"), RESOLUTIONS["720p"])
    reglages = studio.Reglages(
        largeur=largeur,
        hauteur=hauteur,
        duree_photo=nombre(champs, "duree", 3),
        duree_fondu=nombre(champs, "fondu", 0.8),
        zoom=nombre(champs, "zoom", 1.15),
        titre=champs.get("titre", "").strip(),
        sous_titre=champs.get("sous_titre", "").strip(),
        legendes=[ligne.strip() for ligne in champs.get("legendes", "").splitlines()],
        audio=str(audio),
    )
    studio.creer_video(photos, dossier / "video.mp4", reglages)
    return identifiant


class Gestionnaire(BaseHTTPRequestHandler):
    def envoyer(self, code, contenu, type_contenu="text/html; charset=utf-8", entetes=None):
        self.send_response(code)
        self.send_header("Content-Type", type_contenu)
        self.send_header("Content-Length", str(len(contenu)))
        for cle, valeur in (entetes or {}).items():
            self.send_header(cle, valeur)
        self.end_headers()
        self.wfile.write(contenu)

    def do_GET(self):
        if self.path == "/":
            self.envoyer(200, page(FORMULAIRE))
        elif self.path.startswith("/resultat/"):
            identifiant = self.path.split("/")[2]
            self.envoyer(200, page(
                "<h1>✅ Votre vidéo est prête</h1>"
                f"<video src='/video/{html.escape(identifiant)}.mp4' controls autoplay></video>"
                f"<p><a href='/video/{html.escape(identifiant)}.mp4' download='video.mp4'>"
                "⬇️ Télécharger la vidéo</a> · <a href='/'>Créer une autre vidéo</a></p>"
            ))
        elif self.path.startswith("/video/") and self.path.endswith(".mp4"):
            identifiant = self.path[len("/video/"):-len(".mp4")]
            fichier = DOSSIER_TRAVAIL / identifiant / "video.mp4"
            if identifiant.isalnum() and fichier.is_file():
                self.envoyer(200, fichier.read_bytes(), "video/mp4")
            else:
                self.envoyer(404, page("<p>Vidéo introuvable.</p>"))
        else:
            self.envoyer(404, page("<p>Page introuvable. <a href='/'>Accueil</a></p>"))

    def do_POST(self):
        if self.path != "/generer":
            self.envoyer(404, page("<p>Page introuvable.</p>"))
            return
        longueur = int(self.headers.get("Content-Length", 0))
        if longueur > TAILLE_MAX:
            self.envoyer(413, page("<p class='erreur'>Fichiers trop volumineux.</p>"))
            return
        try:
            champs, fichiers = lire_formulaire(
                self.headers.get("Content-Type", ""), self.rfile.read(longueur)
            )
            identifiant = generer_depuis_formulaire(champs, fichiers)
        except (ValueError, OSError, RuntimeError) as erreur:
            self.envoyer(400, page(
                f"<p class='erreur'>Erreur : {html.escape(str(erreur))}</p>"
                "<p><a href='/'>Revenir au formulaire</a></p>"
            ))
            return
        self.envoyer(303, b"", entetes={"Location": f"/resultat/{identifiant}"})


def lancer(port=8000):
    serveur = ThreadingHTTPServer(("127.0.0.1", port), Gestionnaire)
    print(f"Générateur de vidéo disponible sur http://localhost:{port} (Ctrl+C pour arrêter)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrêté.")


if __name__ == "__main__":
    lancer()
