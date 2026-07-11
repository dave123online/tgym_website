from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profil


@receiver(post_save, sender=User)
def creer_profil(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Profil à la création d'un User (ex: via
    `createsuperuser` ou l'admin). Un superuser/staff Django récupère le
    rôle STAFF par défaut, sinon ADHERENT — le staff pourra changer le rôle
    ensuite depuis l'admin (ex: passer un compte en COACH).
    """
    if not created:
        return
    role = Profil.Role.STAFF if (instance.is_staff or instance.is_superuser) else Profil.Role.ADHERENT
    Profil.objects.get_or_create(user=instance, defaults={"role": role})



