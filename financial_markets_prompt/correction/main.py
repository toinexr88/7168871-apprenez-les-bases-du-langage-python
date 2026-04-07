import prompt_templates


def afficher_menu():
    """Affiche le menu interactif et génère le prompt choisi."""
    print("=== GÉNÉRATEUR DE PROMPT — VEILLE MARCHÉS FINANCIERS ===\n")
    print("Choisissez une option :")
    print("1. Prompt principal (analyse complète)")
    print("2. Variante Crypto (deep dive on-chain)")
    print("3. Variante Bourse (analyse sectorielle)")
    print("4. Variante Matières premières (supply/demand)")
    print("5. Variante Macro (corrélations inter-marchés)")

    choix = input("\nVotre choix : ").strip()

    if choix == "1":
        sujet = input("Sujet à analyser : ").strip()
        date = input("Date actuelle : ").strip()
        prompt = prompt_templates.generer_prompt_principal(sujet, date)

    elif choix == "2":
        actif = input("Actif à analyser (ex: BTC) : ").strip()
        date = input("Date : ").strip()
        prompt = prompt_templates.generer_variante("crypto", actif, date)

    elif choix == "3":
        actif = input("Indice ou secteur (ex: S&P500) : ").strip()
        date = input("Date : ").strip()
        prompt = prompt_templates.generer_variante("bourse", actif, date)

    elif choix == "4":
        actif = input("Matière première (ex: Pétrole WTI) : ").strip()
        date = input("Date : ").strip()
        prompt = prompt_templates.generer_variante("matieres_premieres", actif, date)

    elif choix == "5":
        actif = input("Actif de référence (ex: DXY) : ").strip()
        date = input("Date : ").strip()
        prompt = prompt_templates.generer_variante("macro", actif, date)

    else:
        print("Choix invalide.")
        return

    print("\n" + "=" * 60)
    print(prompt)
    print("=" * 60)


if __name__ == "__main__":
    afficher_menu()
