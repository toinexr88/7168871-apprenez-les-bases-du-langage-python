# Générateur de prompt — Veille Marchés Financiers

## Contexte

Vous devez créer un **générateur de prompts** pour un analyste financier IA.
Ce générateur doit produire un prompt structuré et personnalisable pour analyser
les marchés financiers (crypto, bourse, matières premières, macro).

## Instructions

### 1. Créez une fonction `generer_prompt_principal(sujet, date_actuelle)`

Cette fonction reçoit deux paramètres :
- `sujet` : le thème à analyser (ex : `"Bitcoin et le marché crypto"`)
- `date_actuelle` : la date de référence (ex : `"07/04/2026"`)

Elle doit retourner le prompt principal complet en remplaçant les variables
`{{SUJET}}` et `{{DATE_ACTUELLE}}` dans le template.

Le prompt principal doit contenir **6 sections** :
1. `SNAPSHOT MARCHÉ` — tableau de bord des actifs clés
2. `CRYPTOMONNAIES` — analyse BTC, ETH, altcoins, on-chain
3. `MARCHÉS BOURSIERS` — USA, Europe, Asie
4. `MATIÈRES PREMIÈRES` — énergie, métaux, agricole
5. `MACRO & GÉOPOLITIQUE` — banques centrales, données économiques
6. `SYNTHÈSE ACTIONNABLE` — matrice risque/opportunité

### 2. Créez un dictionnaire `VARIANTES` avec 4 variantes de prompts

Chaque variante doit être associée à une clé :
- `"crypto"` — Focus cryptomonnaies (deep dive on-chain)
- `"bourse"` — Focus marchés actions (analyse sectorielle)
- `"matieres_premieres"` — Focus commodités (supply/demand)
- `"macro"` — Focus macro-économique (corrélations inter-marchés)

### 3. Créez une fonction `generer_variante(type_variante, actif, date)`

Cette fonction reçoit :
- `type_variante` : une des 4 clés du dictionnaire `VARIANTES`
- `actif` : l'actif ou indice à analyser (ex : `"BTC"`, `"S&P500"`)
- `date` : la date de référence

Elle retourne le prompt de la variante avec les variables `{{ACTIF}}` (ou
`{{INDICE/SECTEUR}}` / `{{MATIÈRE}}`) et `{{DATE}}` remplacées.

Si `type_variante` n'existe pas dans `VARIANTES`, la fonction doit lever
une exception `ValueError` avec un message explicite.

### 4. Créez une fonction `afficher_menu()` dans `main.py`

Cette fonction affiche un menu interactif permettant à l'utilisateur de :
1. Choisir entre le prompt principal ou une variante
2. Saisir les paramètres nécessaires
3. Afficher le prompt généré

## Exemple d'utilisation attendu

```
=== GÉNÉRATEUR DE PROMPT — VEILLE MARCHÉS FINANCIERS ===

Choisissez une option :
1. Prompt principal (analyse complète)
2. Variante Crypto (deep dive on-chain)
3. Variante Bourse (analyse sectorielle)
4. Variante Matières premières (supply/demand)
5. Variante Macro (corrélations inter-marchés)

Votre choix : 1
Sujet à analyser : Bitcoin et le marché crypto
Date actuelle : 07/04/2026

[Le prompt généré s'affiche ici...]
```

## Fichiers à créer

- `prompt_templates.py` : contient le template, le dictionnaire VARIANTES,
  et les fonctions `generer_prompt_principal()` et `generer_variante()`
- `main.py` : contient la fonction `afficher_menu()` et le point d'entrée
