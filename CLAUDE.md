# CLAUDE.md — Apprenez les bases du langage Python

Ce dépôt contient les exercices du cours OpenClassrooms
["Apprenez les bases du langage Python"](https://openclassrooms.com/fr/courses/7168871-apprenez-les-bases-du-langage-python).

## Structure du dépôt

```
.
├── P1/          # Partie 1 — Fondamentaux Python (5 chapitres : P1C3–P1C7)
├── P2/          # Partie 2 — Flux de contrôle & interaction utilisateur (3 chapitres : P2C1–P2C3)
├── P3/          # Partie 3 — Sujets avancés (3 chapitres : P3C1–P3C3)
└── .claude/
    ├── hooks/session-start.sh   # installe pytest automatiquement en session distante
    ├── skills/run/SKILL.md      # compétence /run pour lancer les scripts
    └── settings.json
```

Chaque chapitre contient deux sous-dossiers :

```
<Partie>/<Chapitre>/
├── énoncé/     # exercice étudiant — main.py est un squelette ("Écrivez votre code ici !")
└── correction/ # solution de référence — main.py est le code complet et fonctionnel
```

## Aperçu des chapitres

| Chapitre | Sujet | Fichiers principaux |
|----------|-------|---------------------|
| P1C3 | `print()` et arithmétique | main.py |
| P1C4 | Variables et f-strings | main.py |
| P1C5 | Types (`str`, `int`, `float`, `bool`) | main.py |
| P1C6 | Listes (append, remove, sort) | main.py |
| P1C7 | Dictionnaires (ajout, accès, suppression) | main.py |
| P2C1 | Calculatrice avec `input()` + validation | main.py |
| P2C2 | Statistiques sur une liste (somme, moyenne, pairs) | main.py |
| P2C3 | Fonctions de calcul de salaire | main.py |
| P3C1 | Imports de modules | main.py, operations.py |
| P3C2 | Scraping HTML avec BeautifulSoup | main.py, index.html |
| P3C3 | Pipeline ETL CSV | main.py, input.csv, tests.py |

## Lancer les exercices

**Toujours faire un `cd` dans le dossier du script avant de le lancer** — les scripts qui lisent des fichiers
(P3C2 lit `index.html`, P3C3 lit `input.csv`) utilisent des chemins relatifs.

```bash
# Scripts non interactifs (P1, P3C1, P3C3)
cd P1/P1C3/correction && python3 main.py

# P3C2 — nécessite index.html dans le répertoire courant
cd P3/P3C2/correction && python3 main.py

# Scripts interactifs (P2 — utilisent input())
cd P2/P2C1/correction
echo -e "4\n2\n+" | python3 main.py
```

Utiliser la compétence `/run` pour lancer les scripts de façon interactive dans Claude Code.

## Lancer les tests

Seul P3C3 dispose de tests automatisés. Les lancer depuis le dossier `correction/`
afin que le répertoire de travail corresponde à ce qu'attend `main.py` :

```bash
cd P3/P3C3/correction
python3 -m pytest --import-mode=importlib ../énoncé/tests.py -v
```

`pytest` est installé automatiquement en session distante par le hook `SessionStart`.

## Conventions de code

- **Langue** : Français — tous les noms de variables, commentaires et sorties `print` sont en français.
- **Version Python** : Python 3 (toujours invoqué avec `python3`).
- **Style** : Code procédural simple ; pas de classes, pas d'annotations de type.
- **Formatage des chaînes** : f-strings privilégiées (`f"Je m'appelle {nom}"`).
- **Validation des entrées** : Utiliser `.isnumeric()` pour vérifier les entiers ; lever `SystemExit()` en cas d'entrée invalide.
- **Commentaires** : Courtes lignes en français expliquant le *pourquoi*, pas le *quoi*.
- **Pas d'environnement virtuel** : Aucun paquet tiers sauf `beautifulsoup4` (P3C2) et `pytest` (installé automatiquement).

## Modèle ETL de P3C3 (l'exercice le plus complexe)

```python
def extract(filename="input.csv") -> list[dict]:
    # lit le CSV avec csv.DictReader ; retourne une liste de dicts

def transform(data) -> list[dict]:
    # calcule salaire = int(heures_travaillees) * 15

def load(data, filename="output.csv"):
    # écrit le CSV avec csv.DictWriter

def main():
    data = extract("input.csv")
    data = transform(data)
    load(data, "output.csv")

if __name__ == "__main__":
    main()
```

Les tests dans `énoncé/tests.py` importent `main` depuis la correction, l'exécutent, vérifient
les valeurs de salaire par nom d'employé, puis suppriment `output.csv`.

## Modèle de module de P3C1

`operations.py` définit `addition(a, b)` et `multiplication(a, b)`.
`main.py` importe le module et appelle `operations.addition(...)`.

## Flux de travail Git

- **Branche principale** : `main` (contenu du cours en amont)
- **Branche de développement** : `claude/claude-md-docs-j7hS3` (branche de travail actuelle)
- Pousser sur la branche de développement ; ne pas pousser directement sur `main`.

```bash
git push -u origin claude/claude-md-docs-j7hS3
```

## Hooks Claude Code

Le hook `SessionStart` (`.claude/hooks/session-start.sh`) s'exécute au démarrage de chaque
session distante et installe `pytest` s'il n'est pas déjà présent.
Il ne fait rien en session locale (`CLAUDE_CODE_REMOTE` doit être égal à `"true"`).
