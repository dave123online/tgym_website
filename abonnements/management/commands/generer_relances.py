from datetime import date, timedelta

from django.core.management.base import BaseCommand

from abonnements.ia_relance import generer_message_relance
from abonnements.models import Abonnement, RelanceMessage


class Command(BaseCommand):
    help = (
        "Détecte les abonnements qui expirent bientôt et génère un message de "
        "relance personnalisé (via Gemini, avec message de secours si l'IA est "
        "indisponible). Les messages restent au statut « à envoyer » : le staff "
        "les consulte dans l'admin et les copie manuellement vers WhatsApp, en "
        "attendant le branchement de l'API WhatsApp Business (Étape 4)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--jours", type=int, default=3,
            help="Nombre de jours avant expiration à partir duquel générer une relance (défaut: 3).",
        )

    def handle(self, *args, **options):
        jours = options["jours"]
        aujourdhui = date.today()
        date_limite = aujourdhui + timedelta(days=jours)

        candidats = Abonnement.objects.filter(
            actif=True,
            date_fin__isnull=False,
            date_fin__gte=aujourdhui,
            date_fin__lte=date_limite,
        ).select_related("user", "plan")

        crees = 0
        ignores = 0

        for abonnement in candidats:
            deja_genere = abonnement.relances.filter(
                date_expiration_ciblee=abonnement.date_fin
            ).exists()
            if deja_genere:
                ignores += 1
                continue

            contenu, genere_par_ia = generer_message_relance(abonnement)
            RelanceMessage.objects.create(
                abonnement=abonnement,
                date_expiration_ciblee=abonnement.date_fin,
                contenu=contenu,
                genere_par_ia=genere_par_ia,
            )
            crees += 1
            origine = "IA" if genere_par_ia else "secours"
            self.stdout.write(f"  → {abonnement} : message généré ({origine})")

        self.stdout.write(self.style.SUCCESS(
            f"{crees} message(s) de relance créé(s), {ignores} déjà existant(s) ignoré(s) "
            f"(fenêtre : abonnements expirant d'ici {jours} jour(s))."
        ))


