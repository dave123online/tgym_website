from django.shortcuts import render

import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Endpoint unique pour la vérification (GET) et la réception (POST)
    des webhooks WhatsApp Business Platform (Meta).

    GET  : challenge de vérification envoyé par Meta lors de la
           configuration du webhook dans le dashboard développeur.
    POST : événements entrants (messages, statuts de livraison, etc.).
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            # Meta exige que le challenge soit renvoyé tel quel, en texte brut.
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("Échec de vérification du webhook WhatsApp (token invalide).")
        return HttpResponseForbidden("Verification token mismatch")

    # POST : réception d'un événement.
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        logger.warning("Payload webhook WhatsApp illisible (JSON invalide).")
        return HttpResponse(status=400)

    # Pour l'instant on se contente de logger le payload complet.
    # À terme : dispatcher selon le "field" (messages, statuses, ...)
    # vers un traitement dédié (ex: mise à jour du statut d'une relance).
    logger.info("Webhook WhatsApp reçu : %s", json.dumps(payload, ensure_ascii=False))

    # Meta exige une réponse 200 rapide, sinon il retente l'envoi.
    return JsonResponse({"status": "received"})
