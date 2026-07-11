"""
Chatbot du site (widget flottant), via Gemini.

Point unique de changement pour l'appel IA — même principe que
`abonnements/ia_relance.py`. Le contexte envoyé au modèle est reconstruit
à chaque appel depuis la base (SiteConfig, Plan, Programme) pour que le
chatbot ne réponde jamais avec des tarifs ou horaires obsolètes.

Ne lève jamais d'exception vers l'appelant : si la clé API est absente ou
l'appel échoue, renvoie un message de repli invitant à contacter le staff
sur WhatsApp plutôt que de casser le widget.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Limite de messages par visiteur par jour (stockée en session), pour une
# UX de courtoisie ("tu as atteint ta limite"). La vraie mesure anti-abus
# est le throttle par IP dans core/views.py (_limite_ip_atteinte), qui ne
# dépend pas du cookie de session — voir audit sécurité 09/07/2026.
LIMITE_MESSAGES_PAR_JOUR = 20

# Nombre d'échanges (user + assistant) conservés dans l'historique de
# session, pour garder le contexte court et donc le coût par appel bas.
MAX_TOURS_HISTORIQUE = 6

MESSAGE_REPLI = (
    "Désolé, je ne suis pas disponible pour le moment. "
    "Écris-nous directement sur WhatsApp, on te répond au plus vite !"
)


def _contexte_site() -> str:
    """Construit le contexte factuel (tarifs, horaires, programme phare...)
    injecté dans le prompt système, pour que le chatbot ne réponde qu'à
    partir de données réelles et à jour — jamais de mémoire/invention."""
    from abonnements.models import Plan
    from coaching.models import Programme
    from core.models import SiteConfig

    config = SiteConfig.get_solo()

    lignes_plans = []
    for plan in Plan.objects.filter(actif=True).order_by("ordre_affichage"):
        lignes_plans.append(f"- {plan.nom} : {plan.prix_affiche()} ({plan.description_courte})")
    plans_texte = "\n".join(lignes_plans) or "Aucune formule active pour le moment."

    programme_phare = Programme.objects.filter(est_phare=True, actif=True).first()
    programme_texte = (
        f"{programme_phare.titre} — {programme_phare.accroche} (durée : {programme_phare.duree})"
        if programme_phare else "Aucun programme phare actuellement mis en avant."
    )

    return (
        f"Nom de la salle : {config.nom}\n"
        f"Slogan : {config.slogan}\n"
        f"Horaires : {config.horaires_texte}\n"
        f"Localisation : {config.adresse_zone} — {config.adresse_reperes}\n"
        f"WhatsApp : {config.whatsapp_numero_1} ou {config.whatsapp_numero_2}\n\n"
        f"Formules tarifaires actives :\n{plans_texte}\n\n"
        f"Programme phare : {programme_texte}"
    )


def _instructions_systeme() -> str:
    return (
        "Tu es l'assistant du site web de T-GYM, une salle de sport au Bénin. "
        "Tu réponds en français, sur un ton chaleureux et motivant, en 2 à 4 "
        "phrases maximum (c'est un widget de chat, pas un article).\n\n"
        "Règles strictes :\n"
        "- N'utilise QUE les informations fournies ci-dessous (tarifs, horaires, "
        "localisation, programme). N'invente jamais un prix, un horaire ou une "
        "adresse qui n'y figure pas.\n"
        "- Tu ne donnes aucun conseil médical, nutritionnel ou d'entraînement "
        "personnalisé (blessure, régime, pathologie) — pour ça, redirige "
        "toujours vers un coach de la salle.\n"
        "- Pour une inscription, une question sur un compte existant, ou tout "
        "ce qui nécessite une action humaine, redirige vers WhatsApp.\n"
        "- Si la question sort du cadre de T-GYM (hors-sujet), dis poliment "
        "que tu ne peux répondre qu'aux questions sur la salle.\n\n"
        f"Informations à jour sur T-GYM :\n{_contexte_site()}"
    )


def obtenir_reponse(historique: list[dict], message: str) -> str:
    """
    historique : liste de {"role": "user"|"model", "text": "..."} (déjà
    tronquée par l'appelant à MAX_TOURS_HISTORIQUE échanges).
    Retourne toujours une chaîne affichable — jamais d'exception.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info("GEMINI_API_KEY absente — chatbot indisponible, message de repli renvoyé.")
        return MESSAGE_REPLI

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        historique_contenu = [
            types.Content(role=tour["role"], parts=[types.Part.from_text(text=tour["text"])])
            for tour in historique
        ]
        chat = client.chats.create(
            model="gemini-1.5-flash",
            history=historique_contenu,
            config=types.GenerateContentConfig(system_instruction=_instructions_systeme()),
        )
        response = chat.send_message(message)
        texte = (response.text or "").strip()
        return texte or MESSAGE_REPLI
    except Exception:
        logger.exception("Échec de l'appel Gemini pour le chatbot du site.")
        return MESSAGE_REPLI


