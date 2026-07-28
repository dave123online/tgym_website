from django.core.management.base import BaseCommand

from abonnements.models import ContactMasse
from comptes.models import Profil
from core.whatsapp import numero_international


class Command(BaseCommand):
    help = (
        "Rattrape les adhérents déjà en base avant la mise en place du signal "
        "comptes.signals.synchroniser_contact_masse : crée (ou réactive) dans "
        "ContactMasse une entrée pour chaque Profil de rôle ADHERENT ayant un "
        "téléphone renseigné. À exécuter une seule fois après déploiement du "
        "signal — celui-ci prend ensuite le relais automatiquement pour tous "
        "les nouveaux comptes et les modifications futures."
    )

    def handle(self, *args, **options):
        profils = (
            Profil.objects.filter(role=Profil.Role.ADHERENT)
            .exclude(telephone="")
            .select_related("user")
        )

        crees, reactives, deja_actifs, ignores_sans_telephone = 0, 0, 0, 0

        for profil in profils:
            telephone = numero_international(profil.telephone)
            nom = profil.user.get_full_name() or profil.user.username
            en_cours = any(a.est_en_cours() for a in profil.user.abonnements.all())

            contact, cree = ContactMasse.objects.get_or_create(
                telephone=telephone,
                defaults={"nom": nom, "actif": en_cours, "note": "Auto : adhérent (backfill)"},
            )

            if cree:
                crees += 1
                statut = "en cours" if en_cours else "abonnement expiré/absent → en pause"
                self.stdout.write(f"  → {nom} ({telephone}) : créé ({statut})")
            elif contact.actif != en_cours:
                contact.actif = en_cours
                contact.save(update_fields=["actif"])
                reactives += 1
                statut = "réactivé" if en_cours else "mis en pause (abonnement expiré)"
                self.stdout.write(f"  → {nom} ({telephone}) : {statut}")
            else:
                deja_actifs += 1

        total_sans_telephone = Profil.objects.filter(
            role=Profil.Role.ADHERENT, telephone=""
        ).count()
        if total_sans_telephone:
            ignores_sans_telephone = total_sans_telephone
            self.stdout.write(
                f"  ⚠ {ignores_sans_telephone} adhérent(s) sans téléphone renseigné, ignoré(s)."
            )

        self.stdout.write(self.style.SUCCESS(
            f"{crees} contact(s) créé(s), {reactives} réactivé(s), "
            f"{deja_actifs} déjà à jour, {ignores_sans_telephone} ignoré(s) (sans téléphone)."
        ))
