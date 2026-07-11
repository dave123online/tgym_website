"""
Envoi automatique via l'API WhatsApp Business Cloud (Meta).

Point unique de changement : tout le reste du code appelle
`envoyer_template_relance`, jamais l'API Meta directement — si un jour
Meta change son API, ou si on ajoute un autre provider, seul ce module
est à modifier.

🔒 Nécessite : compte Meta Business + numéro dédié validé + template
pré-approuvé (hors fenêtre de 24h, un message business-initiated ne peut
PAS contenir de texte libre — uniquement un template Meta avec variables).
C'est pour ça que ce module n'envoie jamais le texte généré par l'IA
(abonnements/ia_relance.py) : ce texte reste réservé à la copie manuelle
par le staff, qui n'est soumise à aucune de ces restrictions.

Tant que les credentials ne sont pas fournis (WHATSAPP_ACCESS_TOKEN /
WHATSAPP_PHONE_NUMBER_ID absents), `envoyer_template_relance` lève
`EnvoiWhatsAppIndisponible` — à charge de l'appelant de garder le
fallback "à envoyer manuellement" actif (voir generer_relances /
envoyer_relances_whatsapp).
"""
import logging

from django.conf import settings

from core.whatsapp import numero_international

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"
TIMEOUT_SECONDS = 10


class EnvoiWhatsAppIndisponible(Exception):
    """Levée quand l'envoi automatique n'est pas possible (credentials
    absents, template non configuré, ou erreur retournée par l'API Meta)."""


def _credentials_pretes() -> bool:
    return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)


def envoyer_template_relance(abonnement) -> dict:
    """
    Envoie le template de relance pré-approuvé pour cet abonnement, avec
    3 variables : prénom, formule, date d'expiration.

    Retourne la réponse JSON de l'API Meta en cas de succès.
    Lève `EnvoiWhatsAppIndisponible` dans tous les cas d'échec (jamais
    d'autre exception ne doit remonter à l'appelant).
    """
    if not _credentials_pretes():
        raise EnvoiWhatsAppIndisponible(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID absents — "
            "envoi automatique indisponible, message laissé pour envoi manuel."
        )

    profil = getattr(abonnement.user, "profil", None)
    telephone = getattr(profil, "telephone", "") or ""
    if not telephone:
        raise EnvoiWhatsAppIndisponible(
            f"Aucun téléphone renseigné pour {abonnement.user.get_username()} "
            "— message laissé pour envoi manuel."
        )

    numero = numero_international(telephone)
    prenom = abonnement.user.first_name or abonnement.user.username
    plan_nom = abonnement.plan.nom
    date_fin = abonnement.date_fin.strftime("%d/%m/%Y") if abonnement.date_fin else "bientôt"

    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": settings.WHATSAPP_TEMPLATE_RELANCE,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUE},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": prenom},
                        {"type": "text", "text": plan_nom},
                        {"type": "text", "text": date_fin},
                    ],
                }
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        import requests

        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        logger.exception("Erreur réseau lors de l'envoi WhatsApp pour l'abonnement #%s", abonnement.pk)
        raise EnvoiWhatsAppIndisponible(f"Erreur réseau : {exc}") from exc

    if response.status_code >= 400:
        logger.error(
            "Échec API WhatsApp pour l'abonnement #%s : HTTP %s — %s",
            abonnement.pk, response.status_code, response.text,
        )
        raise EnvoiWhatsAppIndisponible(
            f"L'API Meta a répondu HTTP {response.status_code} : {response.text}"
        )

    return response.json()


