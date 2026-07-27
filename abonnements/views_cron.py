import logging

from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def declencher_relances(request):
    """
    Endpoint déclenché par un cron externe gratuit (GitHub Actions) pour
    exécuter les deux commandes de relance, faute de Cron Job Render payant.

    Protégé par un token secret dans le header — PAS d'authentification
    session/staff ici, puisque l'appelant est une machine, pas un
    navigateur connecté à l'admin.
    """
    token_recu = request.headers.get("X-Cron-Token", "")
    if not settings.CRON_SECRET_TOKEN or token_recu != settings.CRON_SECRET_TOKEN:
        logger.warning("Tentative d'appel à /cron/relances/ avec un token invalide ou absent.")
        return HttpResponseForbidden("Token invalide.")

    try:
        call_command("generer_relances", jours=3)
        call_command("envoyer_relances_whatsapp")
    except Exception:
        logger.exception("Erreur lors de l'exécution des commandes de relance via cron externe.")
        return JsonResponse({"status": "error"}, status=500)

    return JsonResponse({"status": "ok"})
