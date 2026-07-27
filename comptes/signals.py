from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profil


@receiver(post_save, sender=User)
def creer_profil(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Profil à la création d'un User (ex: via
    `createsuperuser` ou l'admin). Un superuser/staff Django récupère le
    rôle STAFF par défaut, sinon ADHERENT.

    Si le User existe déjà et qu'on lui donne is_staff/is_superuser après
    coup (ex: promotion d'un compte via l'admin), on remonte aussi son
    Profil.role vers STAFF si ce n'est pas déjà le cas — sans jamais
    rétrograder un COACH/STAFF existant si is_staff repasse à False (le
    staff garde la main pour changer le rôle manuellement dans ce sens-là).
    """
    if created:
        role = Profil.Role.STAFF if (instance.is_staff or instance.is_superuser) else Profil.Role.ADHERENT
        Profil.objects.get_or_create(user=instance, defaults={"role": role})
        return

    if instance.is_staff or instance.is_superuser:
        profil, _ = Profil.objects.get_or_create(
            user=instance, defaults={"role": Profil.Role.STAFF}
        )
        if profil.role != Profil.Role.STAFF:
            profil.role = Profil.Role.STAFF
            profil.save(update_fields=["role"])

