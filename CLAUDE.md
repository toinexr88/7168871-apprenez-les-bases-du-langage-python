# CLAUDE.md — Apprenez les bases du langage Python

This repository contains exercises for the OpenClassrooms course
["Apprenez les bases du langage Python"](https://openclassrooms.com/fr/courses/7168871-apprenez-les-bases-du-langage-python).

## Repository layout

```
.
├── P1/          # Part 1 — Python fundamentals (5 chapters: P1C3–P1C7)
├── P2/          # Part 2 — Control flow & user interaction (3 chapters: P2C1–P2C3)
├── P3/          # Part 3 — Advanced topics (3 chapters: P3C1–P3C3)
└── .claude/
    ├── hooks/session-start.sh   # auto-installs pytest in remote sessions
    ├── skills/run/SKILL.md      # /run skill for launching scripts
    └── settings.json
```

Each chapter has two sub-folders:

```
<Part>/<Chapter>/
├── énoncé/     # student exercise — main.py is a stub ("Écrivez votre code ici !")
└── correction/ # reference solution — main.py is the complete working code
```

## Chapter overview

| Chapter | Topic | Notable files |
|---------|-------|---------------|
| P1C3 | `print()` and arithmetic | main.py |
| P1C4 | Variables and f-strings | main.py |
| P1C5 | Types (`str`, `int`, `float`, `bool`) | main.py |
| P1C6 | Lists (append, remove, sort) | main.py |
| P1C7 | Dictionaries (add, access, delete) | main.py |
| P2C1 | Calculator with `input()` + validation | main.py |
| P2C2 | List stats (sum, average, even count) | main.py |
| P2C3 | Salary functions | main.py |
| P3C1 | Module imports | main.py, operations.py |
| P3C2 | BeautifulSoup HTML scraping | main.py, index.html |
| P3C3 | CSV ETL pipeline | main.py, input.csv, tests.py |

## Running exercises

**Always `cd` into the script's own directory first** — scripts that read files
(P3C2 reads `index.html`, P3C3 reads `input.csv`) use relative paths.

```bash
# Non-interactive scripts (P1, P3C1, P3C3)
cd P1/P1C3/correction && python3 main.py

# P3C2 — needs index.html in cwd
cd P3/P3C2/correction && python3 main.py

# Interactive scripts (P2 — use input())
cd P2/P2C1/correction
echo -e "4\n2\n+" | python3 main.py
```

Use the `/run` skill to launch scripts interactively within Claude Code.

## Running tests

Only P3C3 has automated tests. Run them from inside the `correction/` folder
so the working directory matches what `main.py` expects:

```bash
cd P3/P3C3/correction
python3 -m pytest --import-mode=importlib ../énoncé/tests.py -v
```

`pytest` is auto-installed in remote sessions by the `SessionStart` hook.

## Code conventions

- **Language**: French — all variable names, comments, and `print` output are in French.
- **Python version**: Python 3 (always invoked as `python3`).
- **Style**: Plain procedural code; no classes, no type annotations.
- **String formatting**: f-strings preferred (`f"Je m'appelle {nom}"`).
- **Input validation**: Use `.isnumeric()` for integer checks; raise `SystemExit()` on invalid input.
- **Comments**: Short inline French comments that explain the *why*, not the *what*.
- **No virtual environment**: No third-party packages except `beautifulsoup4` (P3C2) and `pytest` (auto-installed).

## P3C3 ETL pattern (the most complex exercise)

```python
def extract(filename="input.csv") -> list[dict]:
    # reads CSV with csv.DictReader; returns list of row dicts

def transform(data) -> list[dict]:
    # computes salaire = int(heures_travaillees) * 15

def load(data, filename="output.csv"):
    # writes CSV with csv.DictWriter

def main():
    data = extract("input.csv")
    data = transform(data)
    load(data, "output.csv")

if __name__ == "__main__":
    main()
```

Tests in `énoncé/tests.py` import `main` from the correction, run it, assert
specific salary values per employee name, then delete `output.csv`.

## P3C1 module pattern

`operations.py` defines `addition(a, b)` and `multiplication(a, b)`.
`main.py` imports the module and calls `operations.addition(...)`.

## Git workflow

- **Main branch**: `main` (upstream course content)
- **Development branch**: `claude/claude-md-docs-j7hS3` (current work branch)
- Push to the development branch; do not push directly to `main`.

```bash
git push -u origin claude/claude-md-docs-j7hS3
```

## Claude Code hooks

`SessionStart` hook (`.claude/hooks/session-start.sh`) runs at the start of
every remote session and installs `pytest` if it is not already present.
It is a no-op in local sessions (`CLAUDE_CODE_REMOTE` must equal `"true"`).
