"""
Générateur de liens WhatsApp pré-remplis (wa.me).

Principe : c'est TOUJOURS le visiteur qui clique et envoie — aucun message
n'est expédié automatiquement par le serveur. Ce module ne fait que
construire l'URL ; il ne touche à aucune API d'envoi.
"""
from urllib.parse import quote

from core.models import SiteConfig


def _numero_par_defaut() -> str:
    config = SiteConfig.get_solo()
    return config.whatsapp_numero_1


def numero_international(numero: str) -> str:
    """
    Convertit un numéro local béninois (ex: '94140535') au format
    international sans '+' (ex: '22994140535'), requis aussi bien par les
    liens wa.me que par l'API WhatsApp Business Cloud.
    Ne touche pas aux numéros déjà préfixés par un indicatif.
    """
    numero = numero.strip().replace(" ", "").replace("-", "")
    if numero.startswith("+"):
        numero = numero[1:]
    if numero.startswith("229"):
        return numero
    return f"229{numero}"


# Alias interne conservé pour ne pas casser le reste de ce module.
_normaliser_numero = numero_international


def build_whatsapp_link(message: str, numero: str | None = None) -> str:
    """
    Construit un lien wa.me avec un message pré-rempli et encodé.
    """
    numero_cible = _normaliser_numero(numero or _numero_par_defaut())
    return f"https://wa.me/{numero_cible}?text={quote(message)}"


def build_plan_whatsapp_link(plan, nom_client: str = "") -> str:
    """
    Message pré-rempli pour une inscription à un plan tarifaire donné.
    """
    if nom_client:
        message = (
            f"Bonjour, je suis {nom_client} et je souhaite m'inscrire "
            f"à la formule « {plan.nom} » ({plan.prix_affiche()})."
        )
    else:
        message = (
            f"Bonjour, je souhaite m'inscrire à la formule « {plan.nom} » "
            f"({plan.prix_affiche()})."
        )
    return build_whatsapp_link(message)


def build_generic_whatsapp_link(sujet: str = "") -> str:
    """
    Message pré-rempli générique (contact / question), utilisé par le
    hub WhatsApp quand la demande ne concerne pas un plan précis.
    """
    if sujet:
        message = f"Bonjour, j'ai une question à propos de : {sujet}."
    else:
        message = "Bonjour, j'aimerais avoir plus d'informations sur T-GYM."
    return build_whatsapp_link(message)



