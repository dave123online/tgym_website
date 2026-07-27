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


def envoyer_texte_libre(numero: str, texte: str) -> dict:
    """
    Envoie un message texte libre (pas un template) — uniquement valide si
    le destinataire a écrit dans les 24h précédentes (fenêtre de service
    ouverte), sinon Meta rejette l'appel. Utilisé pour les réponses du bot
    Gemini et les réponses manuelles du staff, jamais pour du démarchage.

    Gratuit côté facturation Meta (pas de template = pas de coût), donc
    marqué non-facturable dans MessageWhatsApp.
    """
    if not _credentials_pretes():
        raise EnvoiWhatsAppIndisponible(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID absents — envoi indisponible."
        )

    numero_norm = numero_international(numero)
    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_norm,
        "type": "text",
        "text": {"body": texte},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        import requests

        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        logger.exception("Erreur réseau lors de l'envoi WhatsApp texte libre (to=%s)", numero_norm)
        raise EnvoiWhatsAppIndisponible(f"Erreur réseau : {exc}") from exc

    if response.status_code >= 400:
        logger.error(
            "Échec API WhatsApp texte libre (to=%s) : HTTP %s — %s",
            numero_norm, response.status_code, response.text,
        )
        raise EnvoiWhatsAppIndisponible(
            f"L'API Meta a répondu HTTP {response.status_code} : {response.text}"
        )

    reponse_json = response.json()

    from .models import ConversationWhatsApp, MessageWhatsApp

    conversation, _ = ConversationWhatsApp.objects.get_or_create(wa_id=numero_norm.lstrip("+"))
    wamid = (reponse_json.get("messages") or [{}])[0].get("id")
    MessageWhatsApp.objects.create(
        conversation=conversation,
        sens=MessageWhatsApp.Sens.SORTANT,
        wamid=wamid,
        contenu=texte,
        categorie=MessageWhatsApp.Categorie.SESSION,
        est_facturable=False,
        payload_brut=reponse_json,
    )
    return reponse_json


def envoyer_template(
    numero: str, nom_template: str, langue: str, parametres_body: list[str],
    categorie: str | None = None,
) -> dict:
    """
    Envoi générique d'un template WhatsApp vers un numéro donné, sans lien
    avec un Abonnement — utilisé pour l'envoi de masse (ContactMasse) et
    tout futur cas d'usage (annonces, promos...).

    `categorie` : catégorie Meta réelle du template (Marketing/Utility/
    Authentication), utilisée pour un suivi correct de la facturation
    dans MessageWhatsApp. Par défaut Marketing si non précisé (le plus
    prudent : c'est la catégorie la plus chère, donc jamais un
    sous-comptage de coût).

    `parametres_body` : liste de chaînes, dans l'ordre des variables {{1}},
    {{2}}, etc. définies dans le template Meta. Laisser vide si le
    template n'a pas de variable dans son corps.

    Lève `EnvoiWhatsAppIndisponible` dans tous les cas d'échec (mêmes
    règles que `envoyer_template_relance`).
    """
    if not _credentials_pretes():
        raise EnvoiWhatsAppIndisponible(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID absents — envoi indisponible."
        )

    numero_norm = numero_international(numero)

    url = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    components = []
    if parametres_body:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in parametres_body],
        })
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_norm,
        "type": "template",
        "template": {
            "name": nom_template,
            "language": {"code": langue},
            "components": components,
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
        logger.exception("Erreur réseau lors de l'envoi WhatsApp (template=%s, to=%s)", nom_template, numero_norm)
        raise EnvoiWhatsAppIndisponible(f"Erreur réseau : {exc}") from exc

    if response.status_code >= 400:
        logger.error(
            "Échec API WhatsApp (template=%s, to=%s) : HTTP %s — %s",
            nom_template, numero_norm, response.status_code, response.text,
        )
        raise EnvoiWhatsAppIndisponible(
            f"L'API Meta a répondu HTTP {response.status_code} : {response.text}"
        )

    reponse_json = response.json()

    from .models import ConversationWhatsApp, MessageWhatsApp

    conversation, _ = ConversationWhatsApp.objects.get_or_create(wa_id=numero_norm.lstrip("+"))
    wamid = (reponse_json.get("messages") or [{}])[0].get("id")
    MessageWhatsApp.objects.create(
        conversation=conversation,
        sens=MessageWhatsApp.Sens.SORTANT,
        wamid=wamid,
        contenu=f"[Template: {nom_template}] " + " / ".join(parametres_body),
        categorie=categorie or MessageWhatsApp.Categorie.MARKETING,
        est_facturable=True,
        payload_brut=reponse_json,
    )

    return reponse_json


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

    reponse_json = response.json()

    # Journalisation du message sortant dans la conversation, pour l'écran
    # "Conversations WhatsApp" de l'admin (visibilité facturation).
    from .models import ConversationWhatsApp, MessageWhatsApp

    conversation, _ = ConversationWhatsApp.objects.get_or_create(
        wa_id=numero.lstrip("+")
    )
    wamid = (reponse_json.get("messages") or [{}])[0].get("id")
    MessageWhatsApp.objects.create(
        conversation=conversation,
        sens=MessageWhatsApp.Sens.SORTANT,
        wamid=wamid,
        contenu=f"[Template: {settings.WHATSAPP_TEMPLATE_RELANCE}] "
                f"{prenom}, {plan_nom}, expire le {date_fin}",
        categorie=MessageWhatsApp.Categorie.UTILITY,
        est_facturable=True,  # template envoyé proactivement = facturé
        payload_brut=reponse_json,
    )

    return reponse_json

