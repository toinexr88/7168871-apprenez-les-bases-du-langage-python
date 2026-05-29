---
description: Launch and run Python exercise scripts from this course repo
---

# Run skill — Apprenez les bases du langage Python

This repo contains Python CLI scripts organised as course exercises.
Each chapter has an `énoncé/` (exercise) and a `correction/` (solution) folder,
each with a `main.py` entry point.

## Project structure

```
P1/P1C3/énoncé/main.py      ← student exercise
P1/P1C3/correction/main.py  ← reference solution
P2/P2C1/correction/main.py  ← interactive (uses input())
P3/P3C3/correction/main.py  ← reads input.csv, writes output.csv
```

## How to run

**Always `cd` into the script's own directory first** — some scripts
open relative paths (e.g. `input.csv`).

```bash
cd P3/P3C3/correction && python3 main.py
```

For non-interactive scripts (P1, P3):
```bash
cd <chapter>/correction && python3 main.py
```

For interactive scripts (P2 — use `input()`):
```bash
cd P2/<chapter>/correction
echo -e "4\n2\n+" | python3 main.py
```

## How to run tests

```bash
cd P3/P3C3/correction
python3 -m pytest --import-mode=importlib ../énoncé/tests.py -v
```

## Notes

- No virtual environment needed — no third-party dependencies.
- `pytest` is auto-installed by the `SessionStart` hook in remote sessions.
- P3C3 requires `input.csv` to be present in the working directory.
