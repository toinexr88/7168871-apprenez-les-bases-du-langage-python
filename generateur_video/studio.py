"""Cœur du générateur de vidéo.

Ce module transforme une liste de photos en une vidéo MP4 (diaporama animé) :
- un écran titre au début (optionnel),
- un effet "Ken Burns" (zoom lent + léger déplacement) sur chaque photo,
- des fondus enchaînés entre les photos,
- une légende sur chaque photo (optionnelle),
- une piste audio (optionnelle).

Les images sont calculées avec Pillow puis envoyées une par une à `ffmpeg`,
qui se charge de l'encodage vidéo.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXTENSIONS_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}

POLICES_POSSIBLES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
    "arialbd.ttf",
]


@dataclass
class Reglages:
    """Tous les paramètres de la vidéo à générer."""

    largeur: int = 1280
    hauteur: int = 720
    images_par_seconde: int = 30
    duree_photo: float = 3.0  # secondes d'affichage de chaque photo
    duree_fondu: float = 0.8  # secondes de fondu enchaîné entre deux photos
    zoom: float = 1.15  # zoom maximal de l'effet Ken Burns (1.0 = pas de zoom)
    titre: str = ""
    sous_titre: str = ""
    duree_titre: float = 2.5
    legendes: list = field(default_factory=list)
    couleur_fond: tuple = (15, 15, 25)
    audio: str = ""

    def verifier(self):
        """Lève une erreur si un réglage n'a pas de sens."""
        if self.largeur < 16 or self.hauteur < 16:
            raise ValueError("La résolution est trop petite.")
        if self.largeur % 2 or self.hauteur % 2:
            raise ValueError("La largeur et la hauteur doivent être paires.")
        if self.images_par_seconde < 1:
            raise ValueError("Il faut au moins 1 image par seconde.")
        if self.duree_photo <= 0:
            raise ValueError("La durée d'une photo doit être positive.")
        if not 0 <= self.duree_fondu < self.duree_photo:
            raise ValueError("Le fondu doit être plus court que la durée d'une photo.")
        if self.zoom < 1.0:
            raise ValueError("Le zoom doit être supérieur ou égal à 1.")
        if self.titre and self.duree_titre <= self.duree_fondu:
            raise ValueError("L'écran titre doit durer plus longtemps que le fondu.")


def trouver_ffmpeg():
    """Renvoie le chemin de ffmpeg, ou lève une erreur claire s'il manque."""
    chemin = shutil.which("ffmpeg")
    if chemin is None:
        raise RuntimeError(
            "ffmpeg est introuvable. Installez-le (https://ffmpeg.org) "
            "puis relancez le programme."
        )
    return chemin


def charger_police(taille):
    """Charge une police TrueType si possible, sinon la police par défaut."""
    for chemin in POLICES_POSSIBLES:
        try:
            return ImageFont.truetype(chemin, taille)
        except OSError:
            continue
    return ImageFont.load_default(size=taille)


def lister_photos(dossier):
    """Renvoie la liste triée des photos contenues dans un dossier."""
    dossier = Path(dossier)
    if not dossier.is_dir():
        raise FileNotFoundError(f"Le dossier {dossier} n'existe pas.")
    photos = [
        fichier
        for fichier in sorted(dossier.iterdir())
        if fichier.suffix.lower() in EXTENSIONS_IMAGES
    ]
    if not photos:
        raise FileNotFoundError(f"Aucune photo trouvée dans {dossier}.")
    return photos


def preparer_photo(chemin, reglages):
    """Ouvre une photo et l'agrandit pour couvrir l'écran avec la marge du zoom."""
    with Image.open(chemin) as image:
        # Respecte l'orientation enregistrée par l'appareil photo (EXIF)
        image = ImageOps.exif_transpose(image).convert("RGB")
    taille = (
        round(reglages.largeur * reglages.zoom),
        round(reglages.hauteur * reglages.zoom),
    )
    return ImageOps.fit(image, taille, Image.LANCZOS)


def image_ken_burns(photo, progression, numero, reglages):
    """Calcule une image de l'effet Ken Burns.

    `progression` va de 0 (début de la photo) à 1 (fin de la photo).
    Les photos paires zooment vers l'avant, les impaires vers l'arrière,
    et le cadrage glisse doucement d'un côté à l'autre.
    """
    if numero % 2 == 1:
        progression = 1 - progression
    zoom = 1 + (reglages.zoom - 1) * progression
    largeur_cadre = photo.width / zoom
    hauteur_cadre = photo.height / zoom

    marge_x = photo.width - largeur_cadre
    marge_y = photo.height - hauteur_cadre
    # Le sens du glissement horizontal change toutes les deux photos
    glissement = progression if (numero // 2) % 2 == 0 else 1 - progression
    gauche = marge_x * glissement
    haut = marge_y / 2

    cadre = (gauche, haut, gauche + largeur_cadre, haut + hauteur_cadre)
    return photo.resize((reglages.largeur, reglages.hauteur), Image.BILINEAR, box=cadre)


def ajouter_texte_centre(image, texte, police, y, couleur=(255, 255, 255)):
    """Écrit un texte centré horizontalement, avec une ombre pour la lisibilité."""
    dessin = ImageDraw.Draw(image)
    gauche, haut, droite, bas = dessin.textbbox((0, 0), texte, font=police)
    x = (image.width - (droite - gauche)) / 2 - gauche
    decalage = max(2, police.size // 25)
    dessin.text((x + decalage, y + decalage), texte, font=police, fill=(0, 0, 0))
    dessin.text((x, y), texte, font=police, fill=couleur)


def ajouter_legende(image, legende, reglages):
    """Ajoute une légende dans un bandeau semi-transparent en bas de l'image."""
    if not legende:
        return image
    taille_police = max(12, reglages.hauteur // 18)
    police = charger_police(taille_police)
    hauteur_bandeau = int(taille_police * 2)

    bandeau = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(bandeau).rectangle(
        (0, image.height - hauteur_bandeau, image.width, image.height),
        fill=(0, 0, 0, 140),
    )
    resultat = Image.alpha_composite(image.convert("RGBA"), bandeau).convert("RGB")
    y = image.height - hauteur_bandeau + (hauteur_bandeau - taille_police) / 2 - 2
    ajouter_texte_centre(resultat, legende, police, y)
    return resultat


def creer_ecran_titre(reglages):
    """Crée l'image fixe de l'écran titre (fond dégradé + titre + sous-titre)."""
    image = Image.new("RGB", (reglages.largeur, reglages.hauteur), reglages.couleur_fond)
    dessin = ImageDraw.Draw(image)
    r, v, b = reglages.couleur_fond
    for y in range(reglages.hauteur):
        eclat = int(60 * y / reglages.hauteur)
        dessin.line(
            [(0, y), (reglages.largeur, y)],
            fill=(min(255, r + eclat), min(255, v + eclat // 2), min(255, b + eclat * 2)),
        )

    police_titre = charger_police(max(16, reglages.hauteur // 9))
    police_sous_titre = charger_police(max(12, reglages.hauteur // 22))
    centre = reglages.hauteur / 2
    ajouter_texte_centre(image, reglages.titre, police_titre, centre - police_titre.size)
    if reglages.sous_titre:
        ajouter_texte_centre(
            image, reglages.sous_titre, police_sous_titre, centre + police_titre.size * 0.4,
            couleur=(210, 210, 230),
        )
    return image


def generer_images(photos, reglages):
    """Produit, une par une, toutes les images (frames) de la vidéo."""
    ips = reglages.images_par_seconde
    images_par_photo = round(reglages.duree_photo * ips)
    images_fondu = round(reglages.duree_fondu * ips)

    # Les dernières images d'une séquence ne sont pas affichées telles quelles :
    # elles sont gardées de côté pour être mélangées (fondu) avec la séquence suivante.
    a_fondre = []
    if reglages.titre:
        ecran_titre = creer_ecran_titre(reglages)
        for _ in range(round(reglages.duree_titre * ips) - images_fondu):
            yield ecran_titre
        a_fondre = [ecran_titre] * images_fondu

    for numero, chemin in enumerate(photos):
        photo = preparer_photo(chemin, reglages)
        legende = reglages.legendes[numero] if numero < len(reglages.legendes) else ""
        derniere = numero == len(photos) - 1
        prochain_fondu = []

        for i in range(images_par_photo):
            image = image_ken_burns(photo, i / max(1, images_par_photo - 1), numero, reglages)
            image = ajouter_legende(image, legende, reglages)
            if i < len(a_fondre):
                image = Image.blend(a_fondre[i], image, (i + 1) / (len(a_fondre) + 1))
            if not derniere and i >= images_par_photo - images_fondu:
                prochain_fondu.append(image)
            else:
                yield image
        a_fondre = prochain_fondu


def nombre_total_images(nombre_photos, reglages):
    """Calcule combien d'images contiendra la vidéo (utile pour la progression)."""
    ips = reglages.images_par_seconde
    images_fondu = round(reglages.duree_fondu * ips)
    total = nombre_photos * (round(reglages.duree_photo * ips) - images_fondu) + images_fondu
    if reglages.titre:
        total += round(reglages.duree_titre * ips) - images_fondu
    return total


def creer_video(photos, sortie, reglages=None, progression=None):
    """Génère la vidéo MP4 `sortie` à partir de la liste `photos`.

    `progression` est une fonction optionnelle appelée avec (image_actuelle, total)
    pour suivre l'avancement.
    """
    reglages = reglages or Reglages()
    reglages.verifier()
    photos = [Path(photo) for photo in photos]
    if not photos:
        raise ValueError("Il faut au moins une photo pour créer une vidéo.")

    commande = [
        trouver_ffmpeg(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{reglages.largeur}x{reglages.hauteur}",
        "-r", str(reglages.images_par_seconde),
        "-i", "-",
    ]
    if reglages.audio:
        commande += ["-i", str(reglages.audio), "-c:a", "aac", "-shortest"]
    commande += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        "-movflags", "+faststart", str(sortie),
    ]

    total = nombre_total_images(len(photos), reglages)
    processus = subprocess.Popen(commande, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for numero, image in enumerate(generer_images(photos, reglages), start=1):
            processus.stdin.write(image.tobytes())
            if progression:
                progression(numero, total)
        processus.stdin.close()
    except BrokenPipeError:
        pass  # ffmpeg s'est arrêté : l'erreur est lue juste en dessous
    except BaseException:
        processus.kill()
        processus.wait()
        raise
    erreurs = processus.stderr.read().decode(errors="replace")
    if processus.wait() != 0:
        raise RuntimeError(f"ffmpeg a échoué : {erreurs.strip()}")
    return Path(sortie)


def creer_photos_demo(dossier, nombre=4):
    """Crée quelques images colorées pour tester l'application sans vraies photos."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    couleurs = [(231, 76, 60), (46, 204, 113), (52, 152, 219), (241, 196, 15), (155, 89, 182)]
    police = charger_police(120)
    chemins = []
    for numero in range(nombre):
        image = Image.new("RGB", (1600, 1000), couleurs[numero % len(couleurs)])
        dessin = ImageDraw.Draw(image)
        for rayon in range(900, 0, -150):
            teinte = tuple(min(255, c + rayon // 12) for c in couleurs[numero % len(couleurs)])
            dessin.ellipse((800 - rayon, 500 - rayon, 800 + rayon, 500 + rayon), fill=teinte)
        ajouter_texte_centre(image, f"Photo {numero + 1}", police, 430)
        chemin = dossier / f"demo_{numero + 1:02d}.png"
        image.save(chemin)
        chemins.append(chemin)
    return chemins
