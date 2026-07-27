from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from comptes.models import Profil


class Command(BaseCommand):
    help = (
        "Corrige rétroactivement les comptes is_staff/is_superuser=True dont le "
        "Profil.role n'est pas (ou plus) STAFF. Utile pour les comptes créés "
        "avant la sécurisation du signal, ou promus is_staff après coup."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="N'affiche que les comptes concernés, ne modifie rien.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = User.objects.filter(is_staff=True) | User.objects.filter(is_superuser=True)
        qs = qs.distinct()

        corrections = 0
        creations = 0

        for user in qs:
            profil = getattr(user, "profil", None)
            if profil is None:
                creations += 1
                self.stdout.write(f"[Profil manquant] {user.username} -> STAFF")
                if not dry_run:
                    Profil.objects.create(user=user, role=Profil.Role.STAFF)
                continue

            if profil.role != Profil.Role.STAFF:
                corrections += 1
                self.stdout.write(
                    f"[Rôle incorrect] {user.username}: {profil.role} -> STAFF"
                )
                if not dry_run:
                    profil.role = Profil.Role.STAFF
                    profil.save(update_fields=["role"])

        total = corrections + creations
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Aucun compte admin à corriger."))
        elif dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"{total} compte(s) à corriger ({creations} profil(s) à créer, "
                    f"{corrections} rôle(s) à changer). Relancer sans --dry-run pour appliquer."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{total} compte(s) corrigé(s) ({creations} profil(s) créé(s), "
                    f"{corrections} rôle(s) mis à STAFF)."
                )
            )
