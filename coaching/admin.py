from django.contrib import admin

from .models import Programme


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("titre", "duree", "est_phare", "actif", "ordre_affichage")
    list_filter = ("est_phare", "actif")
    list_editable = ("ordre_affichage", "actif", "est_phare")
    search_fields = ("titre", "accroche")
    prepopulated_fields = {"slug": ("titre",)}
    fieldsets = (
        (None, {"fields": ("titre", "slug", "accroche", "duree")}),
        ("Contenu", {"fields": ("objectif", "inclus")}),
        ("Tarif", {"fields": ("prix_fcfa", "prix_note")}),
        ("Affichage", {"fields": ("est_phare", "actif", "ordre_affichage")}),
    )



