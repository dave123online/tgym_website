import json
from datetime import date

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from abonnements.models import Plan
from actualites.models import Actualite
from core.chatbot import LIMITE_MESSAGES_PAR_JOUR, MAX_TOURS_HISTORIQUE, obtenir_reponse
from core.models import PhotoSalle, VideoSalle
from core.whatsapp import build_generic_whatsapp_link, build_plan_whatsapp_link

# Limite globale par IP, indépendante du cookie de session (voir audit
# sécurité 09/07/2026 — le compteur en session seule est contournable en
# ignorant simplement les cookies d'une requête à l'autre). Stockée dans
# le cache Django : par défaut LocMemCache (mémoire du process), ce qui
# suffit pour un seul worker mais doit passer sur un cache partagé
# (Redis/Memcached) si le déploiement tourne plusieurs workers/dynos,
# sans quoi la limite redevient contournable en frappant des workers
# différents.
LIMITE_MESSAGES_PAR_IP_PAR_JOUR = 20


def _adresse_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "inconnue")


def _limite_ip_atteinte(request) -> bool:
    """
    Incrémente et vérifie le compteur par IP. Retourne True si la limite
    du jour est déjà atteinte AVANT cette requête (elle n'est alors pas
    comptée une seconde fois).
    """
    cle = f"chatbot_ip:{date.today().isoformat()}:{_adresse_ip(request)}"
    nombre = cache.get(cle, 0)
    if nombre >= LIMITE_MESSAGES_PAR_IP_PAR_JOUR:
        return True
    cache.set(cle, nombre + 1, timeout=60 * 60 * 26)  # un peu plus qu'un jour
    return False


def accueil(request):
    plans = Plan.objects.filter(actif=True)
    plan_populaire = plans.filter(is_populaire=True).first()
    contact_link = build_generic_whatsapp_link()
    galerie = PhotoSalle.objects.filter(actif=True)[:8]
    videos_programme = VideoSalle.objects.filter(actif=True, programme__actif=True, programme__est_phare=True)
    videos_generales = VideoSalle.objects.filter(actif=True, programme__isnull=True)[:7]
    actus_recentes = Actualite.objects.filter(est_publiee=True)[:3]
    return render(request, "core/accueil.html", {
        "plan_populaire": plan_populaire,
        "contact_link": contact_link,
        "galerie": galerie,
        "videos_programme": videos_programme,
        "videos_generales": videos_generales,
        "actus_recentes": actus_recentes,
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


@require_POST
def chatbot_message(request):
    """
    Point d'entrée du widget de chat. Aucune donnée de conversation n'est
    stockée en base — tout vit dans la session (vidé à la fermeture du
    navigateur ou à l'expiration de session), par simplicité et pour ne
    pas conserver de données personnelles sans nécessité.

    L'historique envoyé à Gemini vient TOUJOURS de la session serveur,
    jamais du client — un visiteur ne peut donc pas injecter de faux
    tours de conversation dans le prompt.
    """
    try:
        donnees = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"erreur": "Requête invalide."}, status=400)

    message = (donnees.get("message") or "").strip()
    if not message:
        return JsonResponse({"erreur": "Message vide."}, status=400)
    if len(message) > 500:
        message = message[:500]

    if _limite_ip_atteinte(request):
        return JsonResponse({
            "reponse": "Tu as atteint la limite de messages pour aujourd'hui. "
                       "Écris-nous directement sur WhatsApp pour continuer !",
            "limite_atteinte": True,
        })

    aujourdhui = date.today().isoformat()
    compteur = request.session.get("chatbot_compteur", {})
    if compteur.get("date") != aujourdhui:
        compteur = {"date": aujourdhui, "nombre": 0}

    if compteur["nombre"] >= LIMITE_MESSAGES_PAR_JOUR:
        return JsonResponse({
            "reponse": "Tu as atteint la limite de messages pour aujourd'hui. "
                       "Écris-nous directement sur WhatsApp pour continuer !",
            "limite_atteinte": True,
        })

    historique = request.session.get("chatbot_historique", [])
    reponse = obtenir_reponse(historique, message)

    historique.append({"role": "user", "text": message})
    historique.append({"role": "model", "text": reponse})
    request.session["chatbot_historique"] = historique[-(MAX_TOURS_HISTORIQUE * 2):]

    compteur["nombre"] += 1
    request.session["chatbot_compteur"] = compteur

    return JsonResponse({"reponse": reponse})



