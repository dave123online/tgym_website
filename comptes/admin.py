from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from abonnements.models import Abonnement

from .models import Profil


class ProfilInline(admin.StackedInline):
    model = Profil
    can_delete = False
    verbose_name_plural = "Profil (rôle)"


class AbonnementInline(admin.TabularInline):
    model = Abonnement
    extra = 0
    fields = ("plan", "date_debut", "date_fin", "actif")
    autocomplete_fields = ("plan",)
    verbose_name_plural = "Abonnements"


class UserAdmin(BaseUserAdmin):
    inlines = (ProfilInline, AbonnementInline)
    list_display = BaseUserAdmin.list_display + ("get_role",)

    def get_inline_instances(self, request, obj=None):
        # Sur l'ajout (obj=None), le signal `creer_profil` crée déjà le Profil
        # juste après le save() du User. Si on affiche aussi l'inline ici, le
        # formset tente de créer un 2e Profil pour le même user au moment du
        # save_related() -> UNIQUE constraint failed sur comptes_profil.user_id.
        # On n'affiche donc l'inline qu'en modification (le Profil existe déjà).
        # AbonnementInline n'a pas ce souci (pas de signal), on le garde même
        # sur le formulaire d'ajout pour pouvoir assigner une formule direct.
        if obj is None:
            return [inline(self.model, self.admin_site) for inline in self.inlines if inline is not ProfilInline]
        return super().get_inline_instances(request, obj)

    def get_role(self, obj):
        return getattr(obj, "profil", None) and obj.profil.get_role_display()
    get_role.short_description = "Rôle"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "telephone", "date_creation")
    list_filter = ("role",)
    list_editable = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "telephone")



