# Fichier à compléter — prompt_templates.py
# Définissez ici le template principal, le dictionnaire VARIANTES,
# et les fonctions generer_prompt_principal() et generer_variante().

PROMPT_PRINCIPAL = """
# Complétez ce template avec les 6 sections de l'analyse
# Utilisez {{SUJET}} et {{DATE_ACTUELLE}} comme variables à remplacer
"""

VARIANTES = {
    # Complétez avec les 4 variantes : crypto, bourse, matieres_premieres, macro
}


def generer_prompt_principal(sujet, date_actuelle):
    """Retourne le prompt principal avec les variables remplacées."""
    # À compléter
    pass


def generer_variante(type_variante, actif, date):
    """Retourne le prompt d'une variante avec les variables remplacées.

    Lève ValueError si type_variante n'est pas dans VARIANTES.
    """
    # À compléter
    pass
