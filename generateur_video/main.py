"""Générateur de vidéo en ligne de commande.

Exemples :
    python main.py --demo
    python main.py mes_photos/ -o vacances.mp4 --titre "Vacances 2026"
    python main.py photo1.jpg photo2.jpg --legendes "Plage" "Montagne" --audio musique.mp3
"""

import argparse
import sys
from pathlib import Path

import studio


def lire_arguments(arguments=None):
    parseur = argparse.ArgumentParser(description="Crée une vidéo diaporama à partir de photos.")
    parseur.add_argument("sources", nargs="*", help="Photos ou dossiers contenant des photos")
    parseur.add_argument("-o", "--sortie", default="video.mp4", help="Fichier vidéo à créer")
    parseur.add_argument("--demo", action="store_true", help="Utilise des photos de démonstration")
    parseur.add_argument("--titre", default="", help="Titre affiché au début")
    parseur.add_argument("--sous-titre", default="", help="Sous-titre de l'écran titre")
    parseur.add_argument("--legendes", nargs="*", default=[], help="Une légende par photo")
    parseur.add_argument("--audio", default="", help="Musique de fond (mp3, wav...)")
    parseur.add_argument("--duree", type=float, default=3.0, help="Secondes par photo")
    parseur.add_argument("--fondu", type=float, default=0.8, help="Secondes de fondu")
    parseur.add_argument("--zoom", type=float, default=1.15, help="Zoom Ken Burns (1 = aucun)")
    parseur.add_argument("--ips", type=int, default=30, help="Images par seconde")
    parseur.add_argument("--resolution", default="1280x720", help="Par exemple 1920x1080")
    return parseur.parse_args(arguments)


def rassembler_photos(sources):
    """Transforme la liste des sources (fichiers et dossiers) en liste de photos."""
    photos = []
    for source in sources:
        chemin = Path(source)
        if chemin.is_dir():
            photos.extend(studio.lister_photos(chemin))
        elif chemin.is_file():
            photos.append(chemin)
        else:
            raise FileNotFoundError(f"{source} est introuvable.")
    return photos


def afficher_progression(actuelle, total):
    pourcentage = actuelle * 100 // total
    barre = "#" * (pourcentage // 4)
    print(f"\rGénération : [{barre:<25}] {pourcentage:3d} %", end="", flush=True)


def main(arguments=None):
    args = lire_arguments(arguments)
    try:
        largeur, hauteur = (int(valeur) for valeur in args.resolution.lower().split("x"))
    except ValueError:
        print("La résolution doit être de la forme LARGEURxHAUTEUR, par exemple 1280x720.")
        return 1

    try:
        if args.demo:
            photos = studio.creer_photos_demo(Path(args.sortie).parent / "photos_demo")
            titre = args.titre or "Démo du générateur"
        else:
            photos = rassembler_photos(args.sources)
            titre = args.titre
        if not photos:
            print("Indiquez des photos, un dossier, ou utilisez --demo.")
            return 1

        reglages = studio.Reglages(
            largeur=largeur,
            hauteur=hauteur,
            images_par_seconde=args.ips,
            duree_photo=args.duree,
            duree_fondu=args.fondu,
            zoom=args.zoom,
            titre=titre,
            sous_titre=args.sous_titre,
            legendes=args.legendes,
            audio=args.audio,
        )
        print(f"{len(photos)} photo(s) → {args.sortie}")
        studio.creer_video(photos, args.sortie, reglages, afficher_progression)
    except (ValueError, FileNotFoundError, RuntimeError) as erreur:
        print(f"\nErreur : {erreur}")
        return 1

    print(f"\nVidéo créée : {Path(args.sortie).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
