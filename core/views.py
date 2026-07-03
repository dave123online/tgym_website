from django.shortcuts import render

from abonnements.models import Plan
from core.whatsapp import build_generic_whatsapp_link, build_plan_whatsapp_link


def accueil(request):
    plans = Plan.objects.filter(actif=True)
    plan_populaire = plans.filter(is_populaire=True).first()
    contact_link = build_generic_whatsapp_link()
    return render(request, "core/accueil.html", {
        "plan_populaire": plan_populaire,
        "contact_link": contact_link,
    })


def methode(request):
    contact_link = build_generic_whatsapp_link("la méthode T-GYM")
    return render(request, "core/methode.html", {"contact_link": contact_link})


def tarifs(request):
    plans = Plan.objects.filter(actif=True)
    plans_premium = plans.filter(categorie=Plan.Categorie.PREMIUM)
    plans_flexibles = plans.filter(categorie=Plan.Categorie.FLEXIBLE)

    # On pré-calcule le lien WhatsApp de chaque plan (pas de logique dans le template)
    for plan in list(plans_premium) + list(plans_flexibles):
        plan.whatsapp_link = build_plan_whatsapp_link(plan)

    return render(request, "core/tarifs.html", {
        "plans_premium": plans_premium,
        "plans_flexibles": plans_flexibles,
    })


def ou_nous_trouver(request):
    contact_link = build_generic_whatsapp_link("comment vous trouver")
    return render(request, "core/ou_nous_trouver.html", {"contact_link": contact_link})
