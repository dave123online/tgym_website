"""
Vues de l'espace staff (hors Django admin) pour le suivi et la réponse aux
conversations WhatsApp. Accès restreint aux comptes ayant un Profil avec le
rôle STAFF (voir comptes.decorators.role_required).
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from comptes.decorators import role_required
from comptes.models import Profil

from .models import ConversationWhatsApp
from .views_reponse import fenetre_service_ouverte


@role_required(Profil.Role.STAFF)
def liste_conversations(request):
    conversations = ConversationWhatsApp.objects.all().prefetch_related("messages")

    filtre = request.GET.get("filtre")
    if filtre == "humain":
        conversations = conversations.filter(mode_bot=ConversationWhatsApp.ModeBot.HUMAIN)
    elif filtre == "bot":
        conversations = conversations.filter(mode_bot=ConversationWhatsApp.ModeBot.BOT)

    # Annote chaque conversation avec son dernier message, sans requête N+1
    # (les messages sont déjà préchargés via prefetch_related ci-dessus).
    for conv in conversations:
        derniers = list(conv.messages.all())
        conv.dernier_message = derniers[-1] if derniers else None

    return render(request, "staff/conversations_liste.html", {
        "conversations": conversations,
        "filtre_actif": filtre,
    })


@role_required(Profil.Role.STAFF)
def detail_conversation(request, pk):
    conversation = get_object_or_404(ConversationWhatsApp, pk=pk)
    fil_messages = conversation.messages.all().order_by("date_envoi")

    return render(request, "staff/conversation_detail.html", {
        "conversation": conversation,
        "fil_messages": fil_messages,
        "fenetre_ouverte": fenetre_service_ouverte(conversation),
        "modes_bot": ConversationWhatsApp.ModeBot.choices,
    })


@role_required(Profil.Role.STAFF)
def changer_mode_conversation(request, pk):
    conversation = get_object_or_404(ConversationWhatsApp, pk=pk)

    if request.method == "POST":
        mode = request.POST.get("mode_bot")
        valeurs_valides = {v for v, _ in ConversationWhatsApp.ModeBot.choices}
        if mode in valeurs_valides:
            conversation.mode_bot = mode
            if mode == ConversationWhatsApp.ModeBot.BOT:
                conversation.raison_escalade = ""
                conversation.save(update_fields=["mode_bot", "raison_escalade"])
            else:
                conversation.save(update_fields=["mode_bot"])
            messages.success(request, "Mode de réponse mis à jour.")
        else:
            messages.error(request, "Mode invalide.")

    return redirect("abonnements:staff_conversation_detail", conversation.pk)

