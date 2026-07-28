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


@receiver(post_save, sender=Profil)
def synchroniser_contact_masse(sender, instance, **kwargs):
    """
    Maintient la liste de diffusion WhatsApp (ContactMasse, dans
    abonnements) synchronisée avec les Profils de rôle ADHERENT.

    Déclenché à chaque save du Profil (création ET modification), pas
    seulement à la création : le téléphone est souvent vide au moment où
    le Profil est créé et rempli après coup, donc on doit re-vérifier à
    chaque sauvegarde plutôt que de rater le cas si on ne regardait qu'à
    la création.

    - Profil ADHERENT + téléphone renseigné → contact créé/réactivé dans
      ContactMasse, dédupliqué par téléphone (un adhérent qui existait
      déjà comme contact manuel, ex: ancien prospect, n'est pas dupliqué).
    - Profil qui n'est plus ADHERENT (passage à COACH/STAFF) → le contact
      correspondant est désactivé (actif=False), jamais supprimé, pour
      garder l'historique et pouvoir le réactiver si le rôle repasse à
      ADHERENT plus tard.

    Import de ContactMasse fait localement (et non en haut du fichier)
    pour éviter tout risque de dépendance circulaire au chargement des
    apps entre `comptes` et `abonnements`.

    Profil.telephone est saisi au format local (ex: 94140535) alors que
    ContactMasse.telephone attend le format international (ex:
    22994140535, requis par l'API WhatsApp) — on passe donc par
    numero_international() pour éviter de créer deux entrées différentes
    pour un même numéro selon le format saisi.

    actif reflète désormais rôle ADHERENT ET abonnement en cours combinés
    (pas juste le rôle) : un adhérent sans abonnement actuellement valide
    est créé/laissé en pause (actif=False) jusqu'à souscription. Le
    signal abonnements.signals.synchroniser_contact_masse_abonnement
    prend ensuite le relais à chaque souscription/expiration.
    """
    from abonnements.models import ContactMasse
    from core.whatsapp import numero_international

    nom = instance.user.get_full_name() or instance.user.username

    if instance.role == Profil.Role.ADHERENT:
        if not instance.telephone:
            return
        telephone = numero_international(instance.telephone)
        en_cours = any(a.est_en_cours() for a in instance.user.abonnements.all())
        contact, cree = ContactMasse.objects.get_or_create(
            telephone=telephone,
            defaults={"nom": nom, "actif": en_cours, "note": "Auto : adhérent"},
        )
        if not cree and contact.actif != en_cours:
            contact.actif = en_cours
            contact.save(update_fields=["actif"])
        return

    # Rôle COACH ou STAFF : on désactive le contact s'il existe, sans le
    # supprimer (garde l'historique, réactivable si le rôle redevient
    # ADHERENT).
    if instance.telephone:
        telephone = numero_international(instance.telephone)
        ContactMasse.objects.filter(telephone=telephone, actif=True).update(actif=False)


