from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("nom", "categorie", "prix_fcfa", "periode", "is_populaire", "actif", "ordre_affichage")
    list_filter = ("categorie", "actif", "is_populaire")
    list_editable = ("ordre_affichage", "actif", "is_populaire")
    search_fields = ("nom",)
    fieldsets = (
        (None, {"fields": ("nom", "categorie", "description_courte")}),
        ("Tarif", {"fields": ("prix_fcfa", "periode")}),
        ("Contenu", {"fields": ("inclus",)}),
        ("Affichage", {"fields": ("is_populaire", "actif", "ordre_affichage")}),
    )
