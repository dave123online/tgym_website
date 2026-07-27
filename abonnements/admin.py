from django.contrib import admin
from django.utils import timezone

from django.shortcuts import render
from django.urls import path

from .forms import EnvoiMasseForm
from .models import Abonnement, ContactMasse, ConversationWhatsApp, MessageWhatsApp, Plan, RelanceMessage, TemplateWhatsApp
from .whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_template


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nom", "categorie", "prix_fcfa", "periode", "is_populaire", "actif", "ordre_affichage")
    list_filter = ("categorie", "actif", "is_populaire")
    list_editable = ("ordre_affichage", "actif", "is_populaire")
    search_fields = ("nom",)
    fieldsets = (
        (None, {"fields": ("nom", "categorie", "description_courte")}),
        ("Tarif", {"fields": ("prix_fcfa", "periode", "duree_jours")}),
        ("Contenu", {"fields": ("inclus",)}),
        ("Affichage", {"fields": ("is_populaire", "actif", "ordre_affichage")}),
    )


@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "date_debut", "date_fin", "actif", "est_en_cours")
    list_filter = ("actif", "plan__categorie", "plan")
    search_fields = ("user__username", "user__first_name", "user__last_name", "plan__nom")
    autocomplete_fields = ("user", "plan")
    date_hierarchy = "date_debut"


@admin.register(RelanceMessage)
class RelanceMessageAdmin(admin.ModelAdmin):
    list_display = (
        "abonnement", "date_expiration_ciblee", "statut", "genere_par_ia",
        "envoye_automatiquement", "date_generation",
    )
    list_filter = ("statut", "genere_par_ia", "envoye_automatiquement")
    search_fields = (
        "abonnement__user__username", "abonnement__user__first_name",
        "abonnement__user__last_name", "contenu",
    )
    readonly_fields = ("date_generation",)
    autocomplete_fields = ("abonnement",)
    date_hierarchy = "date_generation"
    actions = ["marquer_comme_envoye", "marquer_comme_ignore"]
    fieldsets = (
        (None, {"fields": ("abonnement", "date_expiration_ciblee", "statut")}),
        ("Message", {"fields": ("contenu", "genere_par_ia")}),
        ("Suivi de l'envoi", {
            "fields": ("date_generation", "envoye_le", "envoye_par", "envoye_automatiquement"),
        }),
    )

    @admin.action(description="Marquer comme envoyé (je viens de le copier vers WhatsApp)")
    def marquer_comme_envoye(self, request, queryset):
        maj = queryset.update(
            statut=RelanceMessage.Statut.ENVOYE,
            envoye_le=timezone.now(),
            envoye_par=request.user,
        )
        self.message_user(request, f"{maj} message(s) marqué(s) comme envoyé(s).")

    @admin.action(description="Ignorer (ne pas envoyer)")
    def marquer_comme_ignore(self, request, queryset):
        maj = queryset.update(statut=RelanceMessage.Statut.IGNORE)
        self.message_user(request, f"{maj} message(s) marqué(s) comme ignoré(s).")
class MessageWhatsAppInline(admin.TabularInline):
    model = MessageWhatsApp
    extra = 0
    fields = ("sens", "categorie", "contenu", "est_facturable", "statut_livraison", "date_envoi")
    readonly_fields = ("sens", "categorie", "contenu", "est_facturable", "statut_livraison", "date_envoi")
    can_delete = False
    ordering = ("date_envoi",)

    def has_add_permission(self, request, obj=None):
        # Lecture seule : les messages arrivent uniquement via le webhook.
        return False


@admin.register(ConversationWhatsApp)
class ConversationWhatsAppAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "wa_id", "mode_bot", "abonnement",
        "nb_messages", "nb_messages_factures", "derniere_activite",
    )
    list_editable = ("mode_bot",)
    search_fields = ("wa_id", "nom_contact")
    list_filter = ("mode_bot", "derniere_activite")
    autocomplete_fields = ("abonnement",)
    inlines = [MessageWhatsAppInline]
    readonly_fields = ("wa_id", "derniere_activite")
    change_form_template = "admin/abonnements/conversation_change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        from .views_reponse import fenetre_service_ouverte

        conversation = self.get_object(request, object_id)
        extra_context = extra_context or {}
        extra_context["fenetre_ouverte"] = (
            fenetre_service_ouverte(conversation) if conversation else False
        )
        extra_context["fil_messages"] = (
            conversation.messages.order_by("date_envoi") if conversation else []
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def nb_messages(self, obj):
        return obj.messages.count()
    nb_messages.short_description = "Messages"

    def nb_messages_factures(self, obj):
        return obj.messages.filter(est_facturable=True).count()
    nb_messages_factures.short_description = "Dont facturés"


@admin.register(ContactMasse)
class ContactMasseAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "actif", "note", "date_ajout")
    list_editable = ("actif",)
    list_filter = ("actif",)
    search_fields = ("nom", "telephone", "note")
    actions = ["envoyer_template_en_masse"]

    @admin.action(description="Envoyer un template WhatsApp aux contacts sélectionnés")
    def envoyer_template_en_masse(self, request, queryset):
        contacts = queryset.filter(actif=True)

        if "appliquer" in request.POST:
            form = EnvoiMasseForm(request.POST)
            if form.is_valid():
                nom_template = form.cleaned_data["nom_template"]
                langue = form.cleaned_data["langue"]
                parametres = form.parametres_liste()

                reussites, echecs = 0, []
                for contact in contacts:
                    try:
                        envoyer_template(contact.telephone, nom_template, langue, parametres)
                        reussites += 1
                    except EnvoiWhatsAppIndisponible as exc:
                        echecs.append(f"{contact} : {exc}")

                if reussites:
                    self.message_user(request, f"{reussites} message(s) envoyé(s) avec succès.")
                if echecs:
                    self.message_user(
                        request,
                        "Échecs : " + " | ".join(echecs[:10]) + (" ..." if len(echecs) > 10 else ""),
                        level="ERROR",
                    )
                return None
        else:
            form = EnvoiMasseForm()

        return render(
            request,
            "admin/abonnements/envoi_masse.html",
            {
                "form": form,
                "contacts": contacts,
                "nb_contacts": contacts.count(),
                "opts": self.model._meta,
                "title": "Envoyer un template WhatsApp en masse",
            },
        )


@admin.register(TemplateWhatsApp)
class TemplateWhatsAppAdmin(admin.ModelAdmin):
    list_display = ("intitule", "nom_meta", "categorie", "langue", "actif")
    list_filter = ("actif", "categorie", "langue")
    search_fields = ("intitule", "nom_meta")
    change_list_template = "admin/abonnements/templatewhatsapp_changelist.html"
