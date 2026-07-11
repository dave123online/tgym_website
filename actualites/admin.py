from django.contrib import admin

from .models import Actualite


@admin.register(Actualite)
class ActualiteAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "date_publication", "is_featured", "est_publiee")
    list_filter = ("categorie", "is_featured", "est_publiee")
    list_editable = ("is_featured", "est_publiee")
    search_fields = ("titre", "accroche", "corps")
    prepopulated_fields = {"slug": ("titre",)}
    date_hierarchy = "date_publication"
    fieldsets = (
        (None, {"fields": ("titre", "slug", "categorie", "accroche")}),
        ("Contenu", {"fields": ("corps", "image")}),
        ("Publication", {"fields": ("is_featured", "est_publiee", "date_publication")}),
    )



