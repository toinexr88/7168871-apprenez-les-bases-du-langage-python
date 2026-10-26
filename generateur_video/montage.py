"""Assemblage de plusieurs segments vidéo en une seule vidéo.

Les segments peuvent avoir des tailles, des cadences et des formats différents
(vidéos créées par Agnes, diaporamas, clips de votre téléphone…) : ils sont tous
mis au même format, puis mis bout à bout, avec un fondu enchaîné optionnel.

Utilisation en ligne de commande :
    python montage.py debut.mp4 milieu.mp4 fin.mp4 -o film.mp4 --fondu 0.5
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from studio import trouver_ffmpeg

FORMATS = {
    "16:9": (1280, 720),
    "16:9 HD": (1920, 1080),
    "9:16": (720, 1280),
    "1:1": (1080, 1080),
    "4:3": (960, 720),
}


def analyser(chemin):
    """Renvoie la durée (en secondes) d'une vidéo et indique si elle contient du son."""
    ffprobe = str(Path(trouver_ffmpeg()).with_name("ffprobe"))
    resultat = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(chemin)],
        capture_output=True, text=True,
    )
    if resultat.returncode != 0:
        raise ValueError(f"{Path(chemin).name} n'est pas une vidéo lisible.")
    infos = json.loads(resultat.stdout)
    types = [flux.get("codec_type") for flux in infos.get("streams", [])]
    if "video" not in types:
        raise ValueError(f"{Path(chemin).name} ne contient pas d'image vidéo.")
    duree = float(infos.get("format", {}).get("duration") or 0)
    if duree <= 0:
        raise ValueError(f"Impossible de connaître la durée de {Path(chemin).name}.")
    return duree, "audio" in types


def construire_filtre(durees, avec_son, largeur, hauteur, ips, fondu):
    """Construit le « filter_complex » de ffmpeg qui normalise puis enchaîne les segments."""
    lignes = []
    son_present = any(avec_son)
    for i, duree in enumerate(durees):
        # Même taille (avec bandes noires si besoin), même cadence, même format de couleur
        lignes.append(
            f"[{i}:v]scale={largeur}:{hauteur}:force_original_aspect_ratio=decrease,"
            f"pad={largeur}:{hauteur}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
            f"fps={ips},format=yuv420p,trim=duration={duree:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
        if son_present:
            # Un segment sans son reçoit un silence de la même durée
            source = f"[{i}:a]" if avec_son[i] else f"anullsrc=r=48000:cl=stereo,"
            lignes.append(
                f"{source}aresample=48000,aformat=channel_layouts=stereo,"
                f"apad,atrim=duration={duree:.3f},asetpts=PTS-STARTPTS[a{i}]"
            )

    nombre = len(durees)
    if fondu <= 0 or nombre == 1:
        entrees = "".join(f"[v{i}]" + (f"[a{i}]" if son_present else "") for i in range(nombre))
        lignes.append(f"{entrees}concat=n={nombre}:v=1:a={int(son_present)}[v]" + ("[a]" if son_present else ""))
        return ";".join(lignes)

    # Fondus enchaînés : chaque segment commence `fondu` secondes avant la fin du précédent
    video, son, decalage = "[v0]", "[a0]", 0.0
    for i in range(1, nombre):
        decalage += durees[i - 1] - fondu
        sortie_video = "[v]" if i == nombre - 1 else f"[vx{i}]"
        lignes.append(f"{video}[v{i}]xfade=transition=fade:duration={fondu}:offset={decalage:.3f}{sortie_video}")
        video = sortie_video
        if son_present:
            sortie_son = "[a]" if i == nombre - 1 else f"[ax{i}]"
            lignes.append(f"{son}[a{i}]acrossfade=d={fondu}{sortie_son}")
            son = sortie_son
    return ";".join(lignes)


def assembler(segments, sortie, format_video="16:9", ips=30, fondu=0.0):
    """Met bout à bout les vidéos `segments` et enregistre le résultat dans `sortie`."""
    segments = [Path(segment) for segment in segments]
    if not segments:
        raise ValueError("Ajoutez au moins un segment vidéo.")
    if format_video not in FORMATS:
        raise ValueError(f"Format inconnu : {format_video}")
    if fondu < 0:
        raise ValueError("La durée du fondu ne peut pas être négative.")
    for segment in segments:
        if not segment.is_file():
            raise FileNotFoundError(f"{segment} est introuvable.")

    analyses = [analyser(segment) for segment in segments]
    durees = [duree for duree, _ in analyses]
    avec_son = [son for _, son in analyses]
    if len(segments) > 1 and fondu >= min(durees):
        raise ValueError(
            f"Le fondu ({fondu} s) doit être plus court que le segment le plus court "
            f"({min(durees):.1f} s)."
        )

    largeur, hauteur = FORMATS[format_video]
    commande = [trouver_ffmpeg(), "-y", "-loglevel", "error"]
    for segment in segments:
        commande += ["-i", str(segment)]
    commande += [
        "-filter_complex", construire_filtre(durees, avec_son, largeur, hauteur, ips, fondu),
        "-map", "[v]",
    ]
    if any(avec_son):
        commande += ["-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    commande += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(sortie),
    ]
    resultat = subprocess.run(commande, capture_output=True, text=True)
    if resultat.returncode != 0:
        raise RuntimeError(f"ffmpeg a échoué : {resultat.stderr.strip()[-500:]}")
    return Path(sortie)


def main(arguments=None):
    parseur = argparse.ArgumentParser(description="Assemble plusieurs segments en une seule vidéo.")
    parseur.add_argument("segments", nargs="+", help="Vidéos à assembler, dans l'ordre")
    parseur.add_argument("-o", "--sortie", default="montage.mp4")
    parseur.add_argument("--format", default="16:9", choices=list(FORMATS))
    parseur.add_argument("--fondu", type=float, default=0.0, help="Secondes de fondu entre segments")
    parseur.add_argument("--ips", type=int, default=30, help="Images par seconde")
    args = parseur.parse_args(arguments)
    try:
        assembler(args.segments, args.sortie, args.format, args.ips, args.fondu)
    except (ValueError, FileNotFoundError, RuntimeError) as erreur:
        print(f"Erreur : {erreur}")
        return 1
    print(f"Vidéo assemblée : {Path(args.sortie).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
