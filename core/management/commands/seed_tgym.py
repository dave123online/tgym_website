from django.core.management.base import BaseCommand

from abonnements.models import Plan
from core.models import Annonce, SiteConfig


class Command(BaseCommand):
    help = "Charge les données réelles T-GYM (config, plans, annonce de démo)."

    def handle(self, *args, **options):
        config = SiteConfig.get_solo()
        config.nom = "T-GYM"
        config.slogan = "La référence du sport."
        config.horaires_texte = "Ouvert 7j/7 (du Lundi au Dimanche) de 07h00 à 21h00"
        config.whatsapp_numero_1 = "94140535"
        config.whatsapp_numero_2 = "63404995"
        config.facebook_url = "https://facebook.com/tgymbenin"
        config.adresse_zone = "Abomey-Calavi, tronçon Carrefour TOKAN - Carrefour HOUÈTÔ"
        config.adresse_reperes = "À gauche en quittant le carrefour Tokan, ou à droite en quittant le carrefour Houètô."
        config.save()
        self.stdout.write(self.style.SUCCESS("SiteConfig mise à jour."))

        Plan.objects.all().delete()
        Plan.objects.create(
            nom="Premium",
            categorie=Plan.Categorie.PREMIUM,
            prix_fcfa=25000,
            periode="/ mois",
            description_courte="Tout compris",
            inclus=[
                "Accès salle",
                "Suivi coach permanent",
                "Contrôle de résultat",
                "Accompagnement nutritionnel",
            ],
            is_populaire=True,
            ordre_affichage=1,
        )
        Plan.objects.create(
            nom="14 séances / mois",
            categorie=Plan.Categorie.FLEXIBLE,
            prix_fcfa=15000,
            periode="",
            description_courte="14 séances dans le mois",
            ordre_affichage=2,
        )
        Plan.objects.create(
            nom="2 séances / semaine",
            categorie=Plan.Categorie.FLEXIBLE,
            prix_fcfa=10000,
            periode="",
            description_courte="2 séances par semaine",
            ordre_affichage=3,
        )
        Plan.objects.create(
            nom="1 séance / semaine",
            categorie=Plan.Categorie.FLEXIBLE,
            prix_fcfa=5000,
            periode="",
            description_courte="1 séance par semaine",
            ordre_affichage=4,
        )
        self.stdout.write(self.style.SUCCESS("4 formules tarifaires créées."))

        Annonce.objects.get_or_create(
            message="Nouveau programme : 45 jours pour maigrir — places limitées, inscrivez-vous sur WhatsApp !",
            defaults={"actif": True},
        )
        self.stdout.write(self.style.SUCCESS("Annonce de démo créée."))
        self.stdout.write(self.style.SUCCESS("Seed terminé."))
