from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Abonnement, synchroniser_contact_masse_pour_user


@receiver(post_save, sender=Abonnement)
def synchroniser_contact_masse_abonnement(sender, instance, **kwargs):
    """
    À chaque souscription, renouvellement, ou clôture d'un Abonnement
    (actif passé à False), recalcule si le contact WhatsApp correspondant
    (ContactMasse) doit rester actif dans la liste de diffusion — cf.
    synchroniser_contact_masse_pour_user() pour la logique complète.
    """
    synchroniser_contact_masse_pour_user(instance.user)
