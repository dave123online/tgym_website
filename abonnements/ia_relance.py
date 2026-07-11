"""
Génération du message de relance personnalisé, via Gemini.

Point unique de changement : si le fournisseur IA change un jour, seule
cette fonction `generer_message_relance` est à modifier — la commande de
détection et l'admin n'en connaissent que la signature (même logique que
`core/whatsapp.py` pour l'isolation de l'envoi).

Ne lève jamais d'exception vers l'appelant : si la clé API est absente ou
si l'appel échoue, on bascule silencieusement sur un message de secours
(gabarit fixe) pour ne jamais bloquer la tâche planifiée.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _prenom(abonnement) -> str:
    return abonnement.user.first_name or abonnement.user.username


def _date_fin_affichee(abonnement) -> str:
    return abonnement.date_fin.strftime("%d/%m/%Y") if abonnement.date_fin else "bientôt"


def _prompt(abonnement) -> str:
    return (
        "Tu écris un message WhatsApp court et chaleureux, en français, au nom de "
        "la salle de sport T-GYM (Bénin), pour relancer un adhérent dont l'abonnement "
        "arrive à expiration. Ton amical et motivant, jamais culpabilisant.\n\n"
        f"Prénom de l'adhérent : {_prenom(abonnement)}\n"
        f"Formule actuelle : {abonnement.plan.nom}\n"
        f"Date d'expiration : {_date_fin_affichee(abonnement)}\n\n"
        "Contraintes :\n"
        "- 3 à 5 phrases maximum\n"
        "- Pas plus d'un ou deux emojis\n"
        "- Termine par une invitation claire à renouveler\n"
        "- Ne mentionne aucun prix (le staff les confirmera de vive voix)\n"
        "- Signe simplement « L'équipe T-GYM »"
    )


def _message_secours(abonnement) -> str:
    """Gabarit fixe utilisé si l'IA est indisponible (clé absente ou erreur API)."""
    return (
        f"Bonjour {_prenom(abonnement)}, ton abonnement « {abonnement.plan.nom} » "
        f"arrive à expiration le {_date_fin_affichee(abonnement)}. N'hésite pas à "
        "passer nous voir ou à nous répondre pour le renouveler et garder ta lancée. "
        "L'équipe T-GYM."
    )


def generer_message_relance(abonnement) -> tuple[str, bool]:
    """
    Retourne (message, genere_par_ia).

    genere_par_ia=False signifie que le message de secours a été utilisé
    (clé GEMINI_API_KEY absente ou appel Gemini en échec).
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        logger.info(
            "GEMINI_API_KEY absente — message de secours utilisé pour l'abonnement #%s",
            abonnement.pk,
        )
        return _message_secours(abonnement), False

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=_prompt(abonnement),
        )
        texte = (response.text or "").strip()
        if not texte:
            raise ValueError("Réponse vide de Gemini")
        return texte, True
    except Exception:
        logger.exception(
            "Échec de la génération Gemini pour l'abonnement #%s — message de secours utilisé",
            abonnement.pk,
        )
        return _message_secours(abonnement), False


