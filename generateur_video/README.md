# 🎬 Générateur de vidéo

Transforme vos photos en vidéo MP4 animée :

- écran titre avec sous-titre ;
- effet **Ken Burns** (zoom lent et léger glissement) sur chaque photo ;
- **fondus enchaînés** entre les photos ;
- **légendes** en bas de l'image ;
- **musique de fond** (optionnelle) ;
- formats paysage 720p / 1080p, carré (Instagram) ou vertical (Stories).

## Installation

1. Python 3.10 ou plus récent.
2. [ffmpeg](https://ffmpeg.org/download.html) installé et accessible dans le terminal.
3. La bibliothèque Pillow :

```bash
pip install -r requirements.txt
```

## Utilisation

### Interface web

```bash
python app_web.py
```

Ouvrez ensuite <http://localhost:8000>, choisissez vos photos (ou cochez « photos de
démonstration ») puis cliquez sur **Générer la vidéo**. La vidéo s'affiche et peut être
téléchargée.

### Ligne de commande

```bash
# Essai rapide avec des photos générées automatiquement
python main.py --demo

# Toutes les photos d'un dossier, avec un titre et une musique
python main.py mes_photos/ -o vacances.mp4 --titre "Vacances" --sous-titre "Été 2026" --audio musique.mp3

# Photos choisies, avec une légende chacune, en 1080p
python main.py plage.jpg montagne.jpg --legendes "La plage" "La montagne" --resolution 1920x1080
```

`python main.py --help` affiche toutes les options (durée par photo, durée du fondu,
zoom, images par seconde…).

## Organisation du code

| Fichier          | Rôle                                                         |
|------------------|--------------------------------------------------------------|
| `studio.py`      | Cœur du générateur : calcul des images et encodage via ffmpeg |
| `main.py`        | Application en ligne de commande                             |
| `app_web.py`     | Interface web (bibliothèque standard uniquement)             |
| `test_studio.py` | Tests automatiques (`python -m pytest`)                      |
