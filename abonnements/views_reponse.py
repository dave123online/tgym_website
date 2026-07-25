from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from .models import ConversationWhatsApp
from .whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_texte_libre

FENETRE_SERVICE_HEURES = 24


@staff_member_required
def repondre_conversation(request, pk):
    conversation = get_object_or_404(ConversationWhatsApp, pk=pk)

    if request.method == "POST":
        texte = request.POST.get("texte", "").strip()
        if not texte:
            messages.error(request, "Le message est vide.")
        else:
            try:
                envoyer_texte_libre(conversation.wa_id, texte)
                messages.success(request, "Message envoyé.")
                # Repasse la conversation en mode bot après une réponse humaine,
                # sauf si le staff décoche explicitement (via champ caché).
                if request.POST.get("garder_mode_humain") != "1":
                    conversation.mode_bot = ConversationWhatsApp.ModeBot.BOT
                    conversation.raison_escalade = ""
                    conversation.save(update_fields=["mode_bot", "raison_escalade"])
            except EnvoiWhatsAppIndisponible as exc:
                messages.error(request, f"Échec d'envoi : {exc}")

    return redirect("admin:abonnements_conversationwhatsapp_change", conversation.pk)


def fenetre_service_ouverte(conversation: ConversationWhatsApp) -> bool:
    """La fenêtre de service (envoi de texte libre autorisé) est ouverte si
    le client a écrit dans les FENETRE_SERVICE_HEURES dernières heures."""
    dernier_message_entrant = (
        conversation.messages.filter(sens="entrant").order_by("-date_envoi").first()
    )
    if not dernier_message_entrant:
        return False
    ecart = timezone.now() - dernier_message_entrant.date_envoi
    return ecart.total_seconds() < FENETRE_SERVICE_HEURES * 3600
