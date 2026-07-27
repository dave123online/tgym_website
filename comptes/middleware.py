"""
Middleware anti-brute-force par IP, sur les points d'entrée d'authentification
du site (/connexion/ et /admin/login/). Voir audit sécurité 09/07/2026,
finding #6 (backlog "faible", traité ici sans dépendance externe type
django-axes — même approche cache Django que le throttle du chatbot dans
core/views.py).

Principe : compteur d'échecs en cache, par IP, avec verrouillage temporaire
au-delà du seuil. Volontairement simple (par IP seule, pas IP+identifiant) :
cohérent avec le reste du projet, suffisant vu l'entropie des mots de passe
générés (~57 bits, voir PROGRESS.md), pas pensé pour arrêter un botnet
distribué (aucune solution par IP ne le fait de toute façon).

Détection succès/échec : les deux vues concernées (comptes.views.ConnexionView
et l'admin Django) redirigent (302) sur connexion réussie et réaffichent le
formulaire (200) sur échec — heuristique fiable sans avoir à modifier les
vues elles-mêmes.
"""
from datetime import date

from django.core.cache import cache
from django.http import HttpResponse
from django.urls import reverse

SEUIL_TENTATIVES = 10
FENETRE_SECONDES = 15 * 60  # 15 minutes


def _adresse_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "inconnue")


class AntiBruteForceMiddleware:
    """
    À placer après AuthenticationMiddleware dans MIDDLEWARE (ordre sans
    importance ici, ce middleware ne dépend pas de request.user).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Résolus paresseusement (au 1er appel) : urls.py n'est pas encore
        # chargé de façon fiable à l'import de ce module.
        self._chemins = None

    def _chemins_surveilles(self):
        if self._chemins is None:
            self._chemins = {reverse("comptes:connexion"), "/admin/login/"}
        return self._chemins

    def _cle(self, request):
        return f"antibruteforce:{date.today().isoformat()}:{_adresse_ip(request)}"

    def __call__(self, request):
        surveille = (
            request.method == "POST"
            and request.path in self._chemins_surveilles()
        )

        if surveille:
            cle = self._cle(request)
            nombre = cache.get(cle, 0)
            if nombre >= SEUIL_TENTATIVES:
                return HttpResponse(
                    "Trop de tentatives de connexion depuis cette adresse. "
                    "Réessayez dans quelques minutes.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )

        response = self.get_response(request)

        if surveille:
            cle = self._cle(request)
            if response.status_code == 302:
                # Connexion réussie : on efface le compteur pour cette IP.
                cache.delete(cle)
            else:
                # Échec (formulaire réaffiché, généralement 200) : on
                # incrémente. On répare aussi le compteur créé lors du GET
                # initial de la page (aucun, on ne compte que les POST).
                nombre = cache.get(cle, 0)
                cache.set(cle, nombre + 1, timeout=FENETRE_SECONDES)

        return response
