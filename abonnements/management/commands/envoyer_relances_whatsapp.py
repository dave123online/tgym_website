from django.core.management.base import BaseCommand
from django.utils import timezone

from abonnements.models import RelanceMessage
from abonnements.whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_template_relance


class Command(BaseCommand):
    help = (
        "Tente l'envoi automatique (WhatsApp Business Cloud API) des messages "
        "de relance encore au statut « à envoyer ». Si les credentials Meta ne "
        "sont pas configurés, ou si l'envoi échoue pour un abonnement donné, le "
        "message reste simplement « à envoyer » pour copie manuelle par le "
        "staff — cette commande ne bloque jamais rien, même sans être branchée."
    )

    def handle(self, *args, **options):
        en_attente = (
            RelanceMessage.objects.filter(statut=RelanceMessage.Statut.A_ENVOYER)
            .select_related("abonnement__user", "abonnement__plan", "abonnement__user__profil")
        )

        if not en_attente.exists():
            self.stdout.write("Aucun message de relance en attente d'envoi.")
            return

        envoyes = 0
        laisses_en_attente = 0

        for relance in en_attente:
            try:
                envoyer_template_relance(relance.abonnement)
            except EnvoiWhatsAppIndisponible as exc:
                laisses_en_attente += 1
                self.stdout.write(f"  → {relance.abonnement} : laissé en attente ({exc})")
                continue

            relance.statut = RelanceMessage.Statut.ENVOYE
            relance.envoye_le = timezone.now()
            relance.envoye_automatiquement = True
            relance.save(update_fields=["statut", "envoye_le", "envoye_automatiquement"])
            envoyes += 1
            self.stdout.write(self.style.SUCCESS(f"  → {relance.abonnement} : envoyé automatiquement"))

        self.stdout.write(self.style.SUCCESS(
            f"{envoyes} message(s) envoyé(s) automatiquement, "
            f"{laisses_en_attente} laissé(s) pour envoi manuel."
        ))


