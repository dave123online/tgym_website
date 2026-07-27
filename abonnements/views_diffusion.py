from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, render

from .models import Abonnement, TemplateWhatsApp
from .whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_template

CIBLE_CHOICES = [
    ("tous", "Tous les clients enregistrés"),
    ("actifs", "Clients avec un abonnement actif"),
    ("inactifs", "Clients sans abonnement actif"),
    ("custom", "Sélection manuelle"),
]

# Champs client disponibles pour l'injection automatique dans une variable.
CHAMPS_CLIENT = {
    "prenom_client": "Prénom du client",
    "nom_client": "Nom du client",
    "telephone_client": "Numéro du client",
}


def _queryset_cible(cible: str, custom_ids: list[str]) -> "list[User]":
    qs = User.objects.filter(profil__telephone__gt="").select_related("profil")
    ids_actifs = Abonnement.objects.filter(actif=True).values_list("user_id", flat=True)

    if cible == "actifs":
        qs = qs.filter(id__in=ids_actifs)
    elif cible == "inactifs":
        qs = qs.exclude(id__in=ids_actifs)
    elif cible == "custom":
        qs = qs.filter(id__in=custom_ids)
    # "tous" : pas de filtre supplémentaire

    return list(qs)


def _valeur_champ_client(user: User, champ: str) -> str:
    if champ == "prenom_client":
        return user.first_name or user.username
    if champ == "nom_client":
        return user.last_name or ""
    if champ == "telephone_client":
        return user.profil.telephone
    return ""


@staff_member_required
def diffusion_whatsapp(request):
    etape = request.POST.get("etape") or request.GET.get("etape") or "1"

    if request.method == "POST" and etape == "1":
        cible = request.POST.get("cible")
        custom_ids = request.POST.getlist("custom_ids")
        template_id = request.POST.get("template_id")

        if not template_id:
            messages.error(request, "Choisis un template.")
        else:
            template = TemplateWhatsApp.objects.filter(pk=template_id).first()
            destinataires = _queryset_cible(cible, custom_ids)
            if not destinataires:
                messages.error(request, "Aucun destinataire ne correspond à cette cible.")
            else:
                return render(request, "admin/abonnements/diffusion_etape2.html", {
                    "title": "Diffusion WhatsApp — variables",
                    "template": template,
                    "cible": cible,
                    "custom_ids": custom_ids,
                    "nb_destinataires": len(destinataires),
                    "champs_client": CHAMPS_CLIENT,
                })

    if request.method == "POST" and etape == "2":
        template = TemplateWhatsApp.objects.filter(pk=request.POST.get("template_id")).first()
        cible = request.POST.get("cible")
        custom_ids = request.POST.getlist("custom_ids")
        destinataires = _queryset_cible(cible, custom_ids)

        # Pour chaque variable : soit "fixe" avec une valeur texte commune,
        # soit "champ" avec un nom de champ client à résoudre par destinataire.
        specs = []
        for var in template.variables:
            mode = request.POST.get(f"mode_{var}")
            if mode == "fixe":
                specs.append(("fixe", request.POST.get(f"valeur_{var}", "")))
            else:
                specs.append(("champ", request.POST.get(f"champ_{var}")))

        reussites, echecs = 0, []
        for user in destinataires:
            parametres = [
                valeur if mode == "fixe" else _valeur_champ_client(user, valeur)
                for mode, valeur in specs
            ]
            try:
                envoyer_template(
                    user.profil.telephone, template.nom_meta, template.langue, parametres,
                    categorie=template.categorie,
                )
                reussites += 1
            except EnvoiWhatsAppIndisponible as exc:
                echecs.append(f"{user.get_full_name() or user.username} : {exc}")

        if reussites:
            messages.success(request, f"{reussites} message(s) envoyé(s) avec succès.")
        if echecs:
            messages.error(
                request,
                "Échecs : " + " | ".join(echecs[:10]) + (" ..." if len(echecs) > 10 else ""),
            )
        return redirect("admin:abonnements_templatewhatsapp_changelist")

    # Affichage initial (étape 1)
    return render(request, "admin/abonnements/diffusion_etape1.html", {
        "title": "Diffusion WhatsApp",
        "cible_choices": CIBLE_CHOICES,
        "templates": TemplateWhatsApp.objects.filter(actif=True),
        "clients": User.objects.filter(profil__telephone__gt="").select_related("profil"),
    })

