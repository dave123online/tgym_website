from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from .utils import normaliser_telephone


class IdentifiantOuTelephoneBackend(ModelBackend):
    """
    Backend d'authentification UNIQUE du site (voir AUTHENTICATION_BACKENDS
    dans settings.py — ModelBackend n'y figure plus).

    Avant l'audit du 09/07/2026, ce backend s'ajoutait à ModelBackend au
    lieu de le remplacer : les deux tournaient à chaque tentative, donc un
    identifiant existant déclenchait deux hash de mot de passe (un par
    backend) contre un seul pour un identifiant inexistant — un écart de
    timing mesurable à distance permettant d'énumérer les comptes. Ce
    backend fait maintenant systématiquement UN SEUL hash par tentative,
    que l'identifiant existe ou non (réel si trouvé, factice sinon), pour
    que le temps de réponse ne varie plus selon l'existence du compte.

    Permet la connexion via l'identifiant habituel OU via le numéro de
    téléphone du Profil, avec ou sans préfixe (00229/+229/229).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = self._trouver_utilisateur(username)

        if user is None:
            # Hash factice à temps constant (même coût qu'un check_password
            # réel) : empêche de distinguer "identifiant inconnu" de
            # "mauvais mot de passe" par mesure du temps de réponse.
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _trouver_utilisateur(self, identifiant):
        try:
            return User.objects.get(username__iexact=identifiant)
        except User.DoesNotExist:
            pass

        numero = normaliser_telephone(identifiant)
        if not numero:
            return None

        for profil in User.objects.filter(
            profil__telephone__endswith=numero
        ).select_related("profil"):
            if normaliser_telephone(profil.profil.telephone) == numero:
                return profil
        return None
