"""Connexion à l'API vidéo d'Agnes AI (https://platform.agnes-ai.com).

Agnes crée la vidéo à partir d'une description (prompt) et d'une ou plusieurs
photos de référence :
- 1 photo  → mode "img2video" : la photo est animée (elle sert de première image) ;
- 2 photos → mode "keyframe"  : Agnes crée la transition de la 1re à la 2e photo ;
- 2 à 5 photos → mode "reference" : les photos guident le style et le contenu.

La génération est asynchrone : on crée une tâche, puis on consulte son état
jusqu'à ce que la vidéo soit prête, et enfin on la télécharge.

Utilisation en ligne de commande :
    python agnes.py --cle VOTRE_CLE --prompt "La caméra avance doucement" photo.jpg
(la clé peut aussi être placée dans la variable d'environnement AGNES_API_KEY).
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ADRESSE_API = "https://apihub.agnes-ai.com"
MODELES = {
    "agnes-video-2.5-flash": "Agnes Video 2.5 Flash (rapide, 720P)",
    "agnes-video-2.5": "Agnes Video 2.5 (qualité, jusqu'à 2K)",
}
MODES = {
    "auto": "Automatique selon le nombre de photos",
    "img2video": "Animer une photo",
    "keyframe": "Transition entre 2 photos",
    "reference": "Photos de référence (2 à 5)",
}
FORMATS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"]
TAILLES = ["720P", "1080P", "1K", "2K"]
COTE_MAX_PHOTO = 1536  # les photos sont réduites pour alléger l'envoi

MESSAGES_ERREUR = {
    400: "Requête refusée : un paramètre est invalide.",
    401: "Clé API invalide ou expirée. Vérifiez la clé copiée depuis platform.agnes-ai.com.",
    402: "Crédit ou quota Agnes insuffisant.",
    403: "Cette clé API n'a pas accès à ce modèle.",
    413: "Les photos envoyées sont trop lourdes.",
    422: "Un réglage n'est pas accepté (durée, format ou résolution).",
    429: "Trop de demandes : patientez une minute avant de réessayer.",
}


class ErreurAgnes(Exception):
    """Erreur renvoyée par Agnes ou survenue pendant la communication."""


def mode_automatique(nombre_photos):
    """Choisit le mode le plus adapté au nombre de photos fournies."""
    if nombre_photos == 0:
        return "text"
    if nombre_photos == 1:
        return "img2video"
    if nombre_photos == 2:
        return "keyframe"
    return "reference"


def photo_en_base64(source):
    """Réduit une photo (chemin ou octets) et la renvoie encodée en base64 (JPEG)."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((COTE_MAX_PHOTO, COTE_MAX_PHOTO), Image.LANCZOS)
    tampon = io.BytesIO()
    image.save(tampon, "JPEG", quality=90)
    return base64.b64encode(tampon.getvalue()).decode("ascii")


def preparer_requete(prompt, photos, modele="agnes-video-2.5-flash", mode="auto",
                     secondes=5, format_image="16:9", taille="720P"):
    """Construit le corps JSON envoyé à Agnes. `photos` : chemins ou octets."""
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Décrivez la vidéo souhaitée (le prompt est obligatoire).")
    if modele not in MODELES:
        raise ValueError(f"Modèle inconnu : {modele}")
    if format_image not in FORMATS:
        raise ValueError(f"Format inconnu : {format_image}")
    if not 4 <= int(secondes) <= 12:
        raise ValueError("La durée doit être comprise entre 4 et 12 secondes.")
    if "flash" in modele:
        taille = "720P"  # le modèle Flash ne produit que du 720P
    elif taille not in TAILLES:
        raise ValueError(f"Résolution inconnue : {taille}")

    if mode == "auto":
        mode = mode_automatique(len(photos))
    besoins = {"img2video": (1, 1), "keyframe": (2, 2), "reference": (1, 5), "text": (0, 0)}
    if mode not in besoins:
        raise ValueError(f"Mode inconnu : {mode}")
    minimum, maximum = besoins[mode]
    if not minimum <= len(photos) <= maximum:
        attendu = str(minimum) if minimum == maximum else f"entre {minimum} et {maximum}"
        raise ValueError(
            f"Le mode « {MODES.get(mode, mode)} » demande {attendu} photo(s), "
            f"vous en avez fourni {len(photos)}."
        )

    corps = {
        "model": modele,
        "prompt": prompt,
        "mode": mode,
        "seconds": str(int(secondes)),
        "size": taille,
        "aspect_ratio": format_image,
        "n": 1,
    }
    images = [photo_en_base64(photo) for photo in photos]
    if mode == "img2video":
        corps["first_frame"] = images[0]
    elif mode == "keyframe":
        corps["first_frame"], corps["last_frame"] = images
    elif mode == "reference":
        corps["images"] = images
    return corps


class ClientAgnes:
    """Petit client pour l'API vidéo d'Agnes."""

    def __init__(self, cle_api, adresse=None, delai=120):
        cle_api = (cle_api or "").strip()
        if not cle_api:
            raise ValueError("Collez votre clé API Agnes pour lancer la génération.")
        self.cle_api = cle_api
        self.adresse = (adresse or ADRESSE_API).rstrip("/")
        self.delai = delai

    def _appel(self, chemin, corps=None):
        requete = urllib.request.Request(
            self.adresse + chemin,
            data=json.dumps(corps).encode() if corps is not None else None,
            headers={
                "Authorization": f"Bearer {self.cle_api}",
                "Content-Type": "application/json",
            },
            method="POST" if corps is not None else "GET",
        )
        try:
            with urllib.request.urlopen(requete, timeout=self.delai) as reponse:
                return json.loads(reponse.read())
        except urllib.error.HTTPError as erreur:
            detail = erreur.read().decode(errors="replace")[:300]
            message = MESSAGES_ERREUR.get(erreur.code, "Agnes a renvoyé une erreur.")
            raise ErreurAgnes(f"{message} (code {erreur.code} : {detail})") from None
        except (urllib.error.URLError, TimeoutError) as erreur:
            raise ErreurAgnes(f"Impossible de joindre Agnes : {erreur}") from None
        except json.JSONDecodeError:
            raise ErreurAgnes("Réponse illisible reçue d'Agnes.") from None

    def creer_video(self, corps):
        """Lance la génération et renvoie l'identifiant de la vidéo."""
        reponse = self._appel("/v1/videos", corps)
        identifiant = reponse.get("video_id") or reponse.get("id")
        if not identifiant:
            raise ErreurAgnes(f"Agnes n'a pas renvoyé d'identifiant de vidéo : {reponse}")
        return identifiant

    def etat(self, video_id, modele):
        """Renvoie l'état de la vidéo : {"statut", "progression", "url", "erreur"}."""
        reponse = self._appel(f"/agnesapi?video_id={video_id}&model_name={modele}")
        statut = reponse.get("status") or reponse.get("state") or "inconnu"
        if statut in ("completed", "succeeded", "done"):
            statut = "terminee"
        elif statut in ("failed", "error", "cancelled"):
            statut = "echec"
        else:
            statut = "en_cours"
        return {
            "statut": statut,
            "progression": int(reponse.get("progress") or 0),
            "url": reponse.get("url") or reponse.get("video_url"),
            "erreur": reponse.get("error") or reponse.get("message"),
        }

    def attendre(self, video_id, modele, intervalle=5, delai_max=900, progression=None):
        """Consulte l'état jusqu'à la fin de la génération et renvoie l'URL de la vidéo."""
        debut = time.time()
        while time.time() - debut < delai_max:
            etat = self.etat(video_id, modele)
            if progression:
                progression(etat["progression"])
            if etat["statut"] == "terminee":
                if not etat["url"]:
                    raise ErreurAgnes("La vidéo est terminée mais Agnes n'a pas donné son adresse.")
                return etat["url"]
            if etat["statut"] == "echec":
                raise ErreurAgnes(f"La génération a échoué : {etat['erreur']}")
            time.sleep(intervalle)
        raise ErreurAgnes("La génération prend trop de temps, réessayez plus tard.")


def telecharger(url, chemin):
    """Télécharge la vidéo produite par Agnes dans le fichier `chemin`."""
    try:
        with urllib.request.urlopen(url, timeout=300) as reponse:
            Path(chemin).write_bytes(reponse.read())
    except (urllib.error.URLError, TimeoutError) as erreur:
        raise ErreurAgnes(f"Téléchargement de la vidéo impossible : {erreur}") from None
    return Path(chemin)


def main(arguments=None):
    parseur = argparse.ArgumentParser(description="Crée une vidéo avec Agnes AI à partir de photos.")
    parseur.add_argument("photos", nargs="*", help="Photo(s) de référence (0 à 5)")
    parseur.add_argument("--prompt", required=True, help="Description de la vidéo souhaitée")
    parseur.add_argument("--cle", default=os.environ.get("AGNES_API_KEY", ""), help="Clé API Agnes")
    parseur.add_argument("--modele", default="agnes-video-2.5-flash", choices=list(MODELES))
    parseur.add_argument("--mode", default="auto", choices=list(MODES))
    parseur.add_argument("--secondes", type=int, default=5)
    parseur.add_argument("--format", default="16:9", choices=FORMATS)
    parseur.add_argument("--taille", default="720P", choices=TAILLES)
    parseur.add_argument("-o", "--sortie", default="video_agnes.mp4")
    args = parseur.parse_args(arguments)

    try:
        client = ClientAgnes(args.cle)
        corps = preparer_requete(args.prompt, args.photos, args.modele, args.mode,
                                 args.secondes, args.format, args.taille)
        print(f"Envoi à Agnes ({corps['mode']}, {len(args.photos)} photo(s))…")
        video_id = client.creer_video(corps)
        url = client.attendre(
            video_id, args.modele,
            progression=lambda p: print(f"\rGénération par Agnes : {p:3d} %", end="", flush=True),
        )
        telecharger(url, args.sortie)
    except (ValueError, OSError, ErreurAgnes) as erreur:
        print(f"\nErreur : {erreur}")
        return 1
    print(f"\nVidéo créée : {Path(args.sortie).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
