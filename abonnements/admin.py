from django.contrib import admin
from django.utils import timezone

from .models import Abonnement, ConversationWhatsApp, MessageWhatsApp, Plan, RelanceMessage


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
    list_display = ("__str__", "wa_id", "abonnement", "nb_messages", "nb_messages_factures", "derniere_activite")
    search_fields = ("wa_id", "nom_contact")
    list_filter = ("derniere_activite",)
    autocomplete_fields = ("abonnement",)
    inlines = [MessageWhatsAppInline]
    readonly_fields = ("wa_id", "derniere_activite")

    def nb_messages(self, obj):
        return obj.messages.count()
    nb_messages.short_description = "Messages"

    def nb_messages_factures(self, obj):
        return obj.messages.filter(est_facturable=True).count()
    nb_messages_factures.short_description = "Dont facturés"
