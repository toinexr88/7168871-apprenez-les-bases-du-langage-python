import os
import anthropic
import config


def creer_client():
    cle_api = os.environ.get("ANTHROPIC_API_KEY")
    if not cle_api:
        raise ValueError(
            "La variable d'environnement ANTHROPIC_API_KEY n'est pas définie. "
            "Veuillez la définir avant de lancer l'agent."
        )
    return anthropic.Anthropic(api_key=cle_api)


def initialiser_messages():
    return []


def ajouter_message_utilisateur(messages, contenu):
    messages.append({"role": "user", "content": contenu})
    return messages


def ajouter_message_assistant(messages, contenu):
    messages.append({"role": "assistant", "content": contenu})
    return messages


def obtenir_reponse(client, messages):
    reponse = client.messages.create(
        model=config.MODELE,
        max_tokens=config.MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": config.PROMPT_SYSTEME,
                "cache_control": {"type": config.CACHE_TYPE},
            }
        ],
        messages=messages,
    )
    return reponse


def extraire_texte_reponse(reponse):
    for bloc in reponse.content:
        if bloc.type == "text":
            return bloc.text
    return ""


def boucle_conversation(client):
    messages = initialiser_messages()

    while True:
        saisie = input("\nVous : ").strip()

        if not saisie:
            continue

        if saisie.lower() in config.COMMANDES_QUITTER:
            print("\nPeace out ! À bientôt ! ✌️")
            break

        messages = ajouter_message_utilisateur(messages, saisie)

        try:
            reponse = obtenir_reponse(client, messages)
            texte_reponse = extraire_texte_reponse(reponse)
            print(f"\nAgent : {texte_reponse}")
            messages = ajouter_message_assistant(messages, texte_reponse)
        except anthropic.APIConnectionError:
            print("\nErreur : Impossible de se connecter à l'API. Vérifiez votre connexion.")
        except anthropic.AuthenticationError:
            print("\nErreur : Clé API invalide. Vérifiez ANTHROPIC_API_KEY.")
            break
        except anthropic.RateLimitError:
            print("\nErreur : Limite de débit atteinte. Patientez avant de réessayer.")
        except anthropic.APIStatusError as e:
            print(f"\nErreur API ({e.status_code}) : {e.message}")


def main():
    print(config.MESSAGE_BIENVENUE)
    client = creer_client()
    boucle_conversation(client)


if __name__ == "__main__":
    main()
