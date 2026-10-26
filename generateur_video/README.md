# 🎬 Générateur de vidéo

Deux façons de créer une vidéo à partir de vos photos :

1. **✨ Agnes AI** : l'intelligence artificielle d'[Agnes](https://platform.agnes-ai.com)
   génère une vidéo à partir d'une description et d'**une ou plusieurs photos de référence** ;
2. **🎞️ Diaporama** : vos photos sont assemblées sur votre ordinateur en diaporama animé ;
3. **🎬 Montage** : plusieurs segments (vidéos Agnes, diaporamas, vos propres clips)
   sont réunis en **une seule et même vidéo**.

## ☁️ En ligne, sans ordinateur (Render, gratuit)

Tout se fait depuis le téléphone :

1. Créez un compte sur <https://render.com> (« Sign in with GitHub »).
2. Ouvrez ce lien de déploiement :
   <https://render.com/deploy?repo=https://github.com/toinexr88/7168871-apprenez-les-bases-du-langage-python/tree/claude/photo-studio-video-gen-idtkk2>
3. Remplissez les deux champs demandés :
   - `APP_MOT_DE_PASSE` : mot de passe pour entrer dans l'appli (obligatoire, sinon elle est ouverte à tous) ;
   - `AGNES_API_KEY` : votre clé Agnes (facultatif : elle peut aussi être collée dans l'appli).
4. Cliquez sur **Deploy Blueprint** et patientez 3 à 5 minutes.
5. Ouvrez l'adresse `https://generateur-video-xxxx.onrender.com`, puis ajoutez-la à l'écran d'accueil.

Formule gratuite : le service s'endort après 15 min sans visite (réveil en ~1 min) et les vidéos
sont effacées au redémarrage : téléchargez-les dès qu'elles sont prêtes.

## 📱 Utilisation sur téléphone avec un ordinateur

1. Sur l'ordinateur : `python app_web.py`.
2. Le terminal affiche l'adresse **« Sur le téléphone »** (ex. `http://192.168.1.20:8000`).
   Avec `pip install qrcode`, un QR code s'affiche : scannez-le.
3. Ouvrez cette adresse sur le téléphone, **connecté au même Wi-Fi**.
4. Ajoutez-la à l'écran d'accueil (iPhone : Partager → « Sur l'écran d'accueil » ;
   Android : menu ⋮ → « Ajouter à l'écran d'accueil ») : elle s'ouvre alors comme une appli.

Les photos peuvent être prises directement avec l'appareil photo du téléphone.
L'ordinateur doit rester allumé : c'est lui qui crée les vidéos.
Option `--local` : accès réservé à l'ordinateur ; `--port 8080` pour changer de port.
Si le téléphone n'accède pas à la page, autorisez Python dans le pare-feu de l'ordinateur.

## ✨ Création par Agnes AI

1. Créez une clé API sur <https://platform.agnes-ai.com/settings/apiKeys>.
2. Lancez `python app_web.py` et ouvrez <http://localhost:8000> (onglet **Agnes AI**).
3. **Collez votre clé API** dans le champ prévu (case « Mémoriser » pour ne pas la recoller
   à chaque fois : elle reste alors dans votre navigateur uniquement).
4. Ajoutez vos photos de référence et décrivez la vidéo voulue, puis cliquez sur
   **Créer la vidéo avec Agnes**. La progression s'affiche, puis la vidéo à télécharger.

Selon le nombre de photos, le mode « Automatique » choisit :

| Photos | Mode Agnes   | Résultat                                                  |
|--------|--------------|-----------------------------------------------------------|
| 1      | `img2video`  | la photo est animée (elle sert de première image)         |
| 2      | `keyframe`   | transition de la 1re photo vers la 2e                     |
| 3 à 5  | `reference`  | les photos guident le style et le contenu de la vidéo     |

Réglages : modèle (`agnes-video-2.5-flash` rapide en 720P, ou `agnes-video-2.5` jusqu'en 2K),
durée de 4 à 12 secondes, format (16:9, 9:16, 1:1…).

En ligne de commande :

```bash
python agnes.py --cle VOTRE_CLE --prompt "La caméra avance doucement, lumière dorée" photo.jpg
python agnes.py --prompt "Transition fluide" debut.jpg fin.jpg -o transition.mp4   # clé dans AGNES_API_KEY
```

> La génération est facturée par Agnes selon votre forfait. Les photos sont réduites
> (1536 px maximum) avant l'envoi.

## 🎬 Montage : plusieurs segments en une seule vidéo

Agnes crée des vidéos courtes (4 à 12 s) : générez plusieurs segments, puis réunissez-les.

1. Après chaque vidéo Agnes (ou diaporama), cliquez sur **➕ Ajouter au montage**.
2. Dans l'onglet **Montage**, ajoutez si besoin d'autres vidéos déjà créées (➕)
   ou vos propres clips (fichiers vidéo de votre ordinateur ou téléphone).
3. Réorganisez avec ↑ ↓, retirez avec ✕, choisissez le format final et la durée
   du fondu entre segments, puis cliquez sur **Assembler en une seule vidéo**.

Les segments de tailles différentes sont mis au même format (bandes noires si besoin) ;
ceux qui n'ont pas de son reçoivent un silence.

En ligne de commande :

```bash
python montage.py scene1.mp4 scene2.mp4 scene3.mp4 -o film.mp4 --fondu 0.5 --format 16:9
```

## 🎞️ Diaporama local

Transforme vos photos en vidéo MP4 animée, sans connexion internet :

- écran titre avec sous-titre ;
- effet **Ken Burns** (zoom lent et léger glissement) sur chaque photo ;
- **fondus enchaînés** entre les photos ;
- **légendes** en bas de l'image ;
- **musique de fond** (optionnelle) ;
- formats paysage 720p / 1080p, carré (Instagram) ou vertical (Stories).

## Installation

(ffmpeg est nécessaire pour le diaporama et le montage.)

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

Ouvrez ensuite <http://localhost:8000/diaporama>, choisissez vos photos (ou cochez « photos de
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
| `agnes.py`       | Connexion à l'API vidéo d'Agnes AI (+ ligne de commande)      |
| `montage.py`     | Assemblage de plusieurs segments en une seule vidéo (ffmpeg)  |
| `studio.py`      | Cœur du diaporama : calcul des images et encodage via ffmpeg |
| `main.py`        | Application en ligne de commande                             |
| `app_web.py`     | Interface web (bibliothèque standard uniquement)             |
| `test_*.py`      | Tests automatiques (`python -m pytest`)                      |
