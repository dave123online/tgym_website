"""
Décorateurs de contrôle d'accès par rôle.

Prévus pour les prochaines étapes (dashboard adhérent avec abonnement en
cours, dashboard coach avec saisie de contrôle de résultat) — rien d'autre
que la connexion n'est requis à ce stade.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Exige que l'utilisateur connecté ait un Profil avec l'un des rôles donnés.
    Usage : @role_required(Profil.Role.COACH, Profil.Role.STAFF)
    """
    def decorateur(vue):
        @wraps(vue)
        @login_required
        def wrapper(request, *args, **kwargs):
            profil = getattr(request.user, "profil", None)
            if profil is None or profil.role not in roles:
                raise PermissionDenied("Accès réservé à un autre rôle.")
            return vue(request, *args, **kwargs)
        return wrapper
    return decorateur



