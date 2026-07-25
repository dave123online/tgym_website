import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ConversationWhatsApp, MessageWhatsApp

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Endpoint unique pour la vérification (GET) et la réception (POST)
    des webhooks WhatsApp Business Platform (Meta).
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("Échec de vérification du webhook WhatsApp (token invalide).")
        return HttpResponseForbidden("Verification token mismatch")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        logger.warning("Payload webhook WhatsApp illisible (JSON invalide).")
        return HttpResponse(status=400)

    logger.info("Webhook WhatsApp reçu : %s", json.dumps(payload, ensure_ascii=False))

    try:
        _traiter_payload(payload)
    except Exception:
        # On ne fait jamais échouer la réponse HTTP à cause d'un souci de
        # parsing/stockage : Meta réessaierait indéfiniment sinon. On logue
        # l'erreur complète pour investigation manuelle.
        logger.exception("Erreur lors du traitement du payload webhook WhatsApp.")

    return JsonResponse({"status": "received"})


def _traiter_payload(payload: dict) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            for msg in value.get("messages", []):
                _enregistrer_message_entrant(value, msg)

            for statut in value.get("statuses", []):
                _mettre_a_jour_statut(statut)


def _enregistrer_message_entrant(value: dict, msg: dict) -> None:
    wa_id = msg.get("from")
    if not wa_id:
        return

    nom_contact = ""
    for contact in value.get("contacts", []):
        if contact.get("wa_id") == wa_id:
            nom_contact = contact.get("profile", {}).get("name", "")
            break

    conversation, created = ConversationWhatsApp.objects.get_or_create(
        wa_id=wa_id, defaults={"nom_contact": nom_contact}
    )
    if not created and nom_contact and conversation.nom_contact != nom_contact:
        conversation.nom_contact = nom_contact
        conversation.save(update_fields=["nom_contact"])

    contenu = _extraire_contenu(msg)

    MessageWhatsApp.objects.update_or_create(
        wamid=msg.get("id"),
        defaults={
            "conversation": conversation,
            "sens": MessageWhatsApp.Sens.ENTRANT,
            "contenu": contenu,
            "categorie": MessageWhatsApp.Categorie.SESSION,
            "est_facturable": False,  # les messages reçus ne sont jamais facturés
            "payload_brut": msg,
        },
    )
    # Toute réponse envoyée dans les 24h suivant CE message sera gratuite —
    # rien à calculer ici, c'est juste pour information au moment de l'envoi.


def _extraire_contenu(msg: dict) -> str:
    type_msg = msg.get("type")
    if type_msg == "text":
        return msg.get("text", {}).get("body", "")
    if type_msg in ("image", "video", "audio", "document", "sticker"):
        return f"[{type_msg}] {msg.get(type_msg, {}).get('caption', '')}".strip()
    if type_msg == "button":
        return msg.get("button", {}).get("text", "")
    if type_msg == "interactive":
        interactive = msg.get("interactive", {})
        return (
            interactive.get("button_reply", {}).get("title")
            or interactive.get("list_reply", {}).get("title")
            or ""
        )
    return f"[{type_msg or 'inconnu'}]"


def _mettre_a_jour_statut(statut: dict) -> None:
    wamid = statut.get("id")
    if not wamid:
        return
    MessageWhatsApp.objects.filter(wamid=wamid).update(
        statut_livraison=statut.get("status", "")
    )
