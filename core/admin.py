from django.contrib import admin

from .models import Annonce, SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identité", {"fields": ("nom", "slogan")}),
        ("Horaires", {"fields": ("horaires_texte",)}),
        ("Contacts WhatsApp", {"fields": ("whatsapp_numero_1", "whatsapp_numero_2")}),
        ("Réseaux sociaux", {"fields": ("facebook_url",)}),
        ("Localisation", {"fields": ("adresse_zone", "adresse_reperes", "latitude", "longitude")}),
    )

    def has_add_permission(self, request):
        # Singleton : on empêche d'en créer une deuxième depuis l'admin
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ("message", "actif", "date_debut", "date_fin", "statut_visible")
    list_filter = ("actif",)
    search_fields = ("message",)

    @admin.display(description="Visible actuellement", boolean=True)
    def statut_visible(self, obj):
        return obj.est_visible()
