"""Interface web du générateur de vidéo.

Lancement :
    python app_web.py
puis ouvrir http://localhost:8000 dans un navigateur.

Deux outils sont proposés :
- « Agnes AI » : l'intelligence artificielle d'Agnes crée la vidéo à partir
  d'une description et d'une ou plusieurs photos de référence (clé API requise) ;
- « Diaporama » : les photos sont assemblées localement en diaporama animé.

Le serveur n'utilise que la bibliothèque standard de Python (http.server),
en plus de Pillow et ffmpeg utilisés par `studio.py`.
"""

import html
import json
import tempfile
import uuid
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import agnes
import studio

DOSSIER_TRAVAIL = Path(tempfile.gettempdir()) / "generateur_video"
TAILLE_MAX = 300 * 1024 * 1024  # 300 Mo d'envoi au maximum
TRAVAUX_AGNES = {}  # générations Agnes en cours : identifiant → informations
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
nav { display: flex; gap: 8px; margin-bottom: 18px; }
nav a { padding: 8px 14px; border-radius: 8px; background: #1f1f2e; text-decoration: none; }
nav a.actif { background: #6c63ff; color: white; }
.cle { display: flex; gap: 8px; } .cle input { flex: 1; }
.cle button { padding: 8px 12px; background: #3a3a55; }
.apercus { display: flex; flex-wrap: wrap; gap: 8px; }
.apercus img { width: 84px; height: 84px; object-fit: cover; border-radius: 8px; }
progress { width: 100%; height: 14px; }
#resultat { display: grid; gap: 12px; margin-top: 18px; }
"""

NAVIGATION = """
<nav><a href="/" class="{agnes}">✨ Agnes AI</a>
<a href="/diaporama" class="{diaporama}">🎞️ Diaporama</a></nav>
"""

OPTIONS_MODELES = "".join(f"<option value='{m}'>{n}</option>" for m, n in agnes.MODELES.items())
OPTIONS_MODES = "".join(f"<option value='{m}'>{n}</option>" for m, n in agnes.MODES.items())
OPTIONS_FORMATS = "".join(f"<option>{f}</option>" for f in agnes.FORMATS)
OPTIONS_TAILLES = "".join(f"<option>{t}</option>" for t in agnes.TAILLES)

FORMULAIRE_AGNES = NAVIGATION.format(agnes="actif", diaporama="") + f"""
<h1>✨ Vidéo créée par Agnes AI</h1>
<p>Ajoutez une ou plusieurs photos de référence et décrivez la vidéo voulue :
Agnes génère la vidéo par intelligence artificielle.</p>
<form id="formulaire">
  <label>Clé API Agnes
    <small>À créer sur <a href="https://platform.agnes-ai.com/settings/apiKeys" target="_blank">
    platform.agnes-ai.com</a>. Elle n'est envoyée qu'à Agnes.</small>
    <span class="cle">
      <input type="password" name="cle" id="cle" placeholder="Collez votre clé API ici"
             autocomplete="off" required>
      <button type="button" id="afficher">👁️</button>
    </span>
  </label>
  <label><span><input type="checkbox" id="memoriser"> Mémoriser la clé dans ce navigateur</span></label>
  <label>Photos de référence <small>(1 à 5 — 1 : la photo est animée,
    2 : transition de la 1re à la 2e, 3 à 5 : références de style et de contenu)</small>
    <input type="file" name="photos" id="photos" accept="image/*" multiple required>
  </label>
  <div class="apercus" id="apercus"></div>
  <label>Description de la vidéo
    <textarea name="prompt" rows="3" required
      placeholder="Ex. : la caméra avance lentement, les feuilles bougent avec le vent, lumière dorée de fin de journée"></textarea>
  </label>
  <div class="ligne">
    <label>Mode <select name="mode">{OPTIONS_MODES}</select></label>
    <label>Modèle <select name="modele">{OPTIONS_MODELES}</select></label>
    <label>Durée (s) <input type="number" name="secondes" value="5" min="4" max="12"></label>
    <label>Format <select name="format">{OPTIONS_FORMATS}</select></label>
    <label>Résolution <small>(Flash : 720P)</small> <select name="taille">{OPTIONS_TAILLES}</select></label>
  </div>
  <button type="submit" id="lancer">Créer la vidéo avec Agnes</button>
</form>
<div id="resultat"></div>
<script>
const champCle = document.getElementById("cle");
const memoriser = document.getElementById("memoriser");
try {{
  const cle = localStorage.getItem("cle_agnes");
  if (cle) {{ champCle.value = cle; memoriser.checked = true; }}
}} catch (e) {{}}
document.getElementById("afficher").onclick = () => {{
  champCle.type = champCle.type === "password" ? "text" : "password";
}};
document.getElementById("photos").onchange = (evenement) => {{
  const apercus = document.getElementById("apercus");
  apercus.innerHTML = "";
  for (const fichier of evenement.target.files) {{
    const image = document.createElement("img");
    image.src = URL.createObjectURL(fichier);
    apercus.appendChild(image);
  }}
}};
const resultat = document.getElementById("resultat");
function afficher(contenu) {{ resultat.innerHTML = contenu; }}
function erreur(message) {{
  const p = document.createElement("p");
  p.className = "erreur";
  p.textContent = "Erreur : " + message;
  resultat.replaceChildren(p);
  document.getElementById("lancer").disabled = false;
}}
async function suivre(travail) {{
  const reponse = await fetch("/agnes/etat/" + travail);
  const etat = await reponse.json();
  if (etat.erreur) return erreur(etat.erreur);
  if (etat.statut === "terminee") {{
    document.getElementById("lancer").disabled = false;
    return afficher(`<h2>✅ Votre vidéo est prête</h2>
      <video src="${{etat.video}}" controls autoplay loop></video>
      <a href="${{etat.video}}" download="video_agnes.mp4">⬇️ Télécharger la vidéo</a>`);
  }}
  afficher(`<p>Agnes crée votre vidéo… ${{etat.progression}} %</p>
    <progress max="100" value="${{etat.progression}}"></progress>
    <small>Cela prend en général une à quelques minutes. Gardez cette page ouverte.</small>`);
  setTimeout(() => suivre(travail), 5000);
}}
document.getElementById("formulaire").onsubmit = async (evenement) => {{
  evenement.preventDefault();
  try {{
    if (memoriser.checked) localStorage.setItem("cle_agnes", champCle.value.trim());
    else localStorage.removeItem("cle_agnes");
  }} catch (e) {{}}
  document.getElementById("lancer").disabled = true;
  afficher("<p>Envoi des photos à Agnes…</p>");
  try {{
    const reponse = await fetch("/agnes/lancer", {{ method: "POST", body: new FormData(evenement.target) }});
    const donnees = await reponse.json();
    if (donnees.erreur) return erreur(donnees.erreur);
    suivre(donnees.travail);
  }} catch (e) {{
    erreur("le serveur local ne répond pas (" + e.message + ")");
  }}
}};
</script>
"""

FORMULAIRE = NAVIGATION.format(agnes="", diaporama="actif") + """
<h1>🎞️ Diaporama animé</h1>
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


def lancer_agnes(champs, fichiers):
    """Envoie la demande à Agnes et renvoie l'identifiant local du travail."""
    client = agnes.ClientAgnes(champs.get("cle", ""))
    photos = [contenu for _, contenu in sorted(fichiers.get("photos", []))]
    modele = champs.get("modele", "agnes-video-2.5-flash")
    try:
        secondes = int(champs.get("secondes") or 5)
    except ValueError:
        raise ValueError("La durée doit être un nombre entier de secondes.")
    corps = agnes.preparer_requete(
        champs.get("prompt", ""), photos, modele, champs.get("mode", "auto"),
        secondes, champs.get("format", "16:9"), champs.get("taille", "720P"),
    )
    video_id = client.creer_video(corps)
    travail = uuid.uuid4().hex[:12]
    TRAVAUX_AGNES[travail] = {"client": client, "video_id": video_id, "modele": modele}
    return travail


def etat_agnes(travail):
    """Consulte Agnes ; quand la vidéo est prête, la télécharge pour l'afficher."""
    infos = TRAVAUX_AGNES.get(travail)
    if infos is None:
        raise ValueError("Génération inconnue (le serveur a peut-être redémarré).")
    fichier = DOSSIER_TRAVAIL / travail / "video.mp4"
    if fichier.is_file():
        return {"statut": "terminee", "video": f"/video/{travail}.mp4"}

    etat = infos["client"].etat(infos["video_id"], infos["modele"])
    if etat["statut"] == "echec":
        raise agnes.ErreurAgnes(f"Agnes n'a pas pu créer la vidéo : {etat['erreur']}")
    if etat["statut"] == "terminee":
        if not etat["url"]:
            raise agnes.ErreurAgnes("Vidéo terminée, mais Agnes n'a pas fourni son adresse.")
        fichier.parent.mkdir(parents=True, exist_ok=True)
        agnes.telecharger(etat["url"], fichier)
        return {"statut": "terminee", "video": f"/video/{travail}.mp4"}
    return {"statut": "en_cours", "progression": etat["progression"]}


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

    def envoyer_json(self, donnees, code=200):
        self.envoyer(code, json.dumps(donnees).encode(), "application/json")

    def do_GET(self):
        if self.path == "/":
            self.envoyer(200, page(FORMULAIRE_AGNES))
        elif self.path == "/diaporama":
            self.envoyer(200, page(FORMULAIRE))
        elif self.path.startswith("/agnes/etat/"):
            try:
                self.envoyer_json(etat_agnes(self.path.split("/")[3]))
            except (ValueError, OSError, agnes.ErreurAgnes) as erreur:
                self.envoyer_json({"erreur": str(erreur)})
        elif self.path.startswith("/resultat/"):
            identifiant = self.path.split("/")[2]
            self.envoyer(200, page(
                "<h1>✅ Votre vidéo est prête</h1>"
                f"<video src='/video/{html.escape(identifiant)}.mp4' controls autoplay></video>"
                f"<p><a href='/video/{html.escape(identifiant)}.mp4' download='video.mp4'>"
                "⬇️ Télécharger la vidéo</a> · <a href='/diaporama'>Créer une autre vidéo</a></p>"
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
        if self.path not in ("/generer", "/agnes/lancer"):
            self.envoyer(404, page("<p>Page introuvable.</p>"))
            return
        longueur = int(self.headers.get("Content-Length", 0))
        if longueur > TAILLE_MAX:
            self.envoyer(413, page("<p class='erreur'>Fichiers trop volumineux.</p>"))
            return
        if self.path == "/agnes/lancer":
            try:
                champs, fichiers = lire_formulaire(
                    self.headers.get("Content-Type", ""), self.rfile.read(longueur)
                )
                self.envoyer_json({"travail": lancer_agnes(champs, fichiers)})
            except (ValueError, OSError, agnes.ErreurAgnes) as erreur:
                self.envoyer_json({"erreur": str(erreur)})
            return
        try:
            champs, fichiers = lire_formulaire(
                self.headers.get("Content-Type", ""), self.rfile.read(longueur)
            )
            identifiant = generer_depuis_formulaire(champs, fichiers)
        except (ValueError, OSError, RuntimeError) as erreur:
            self.envoyer(400, page(
                f"<p class='erreur'>Erreur : {html.escape(str(erreur))}</p>"
                "<p><a href='/diaporama'>Revenir au formulaire</a></p>"
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
