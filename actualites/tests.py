from django.test import TestCase
from django.urls import reverse

from .models import Actualite


class ActualiteModelTests(TestCase):
    def test_slug_genere_automatiquement_depuis_le_titre(self):
        actu = Actualite.objects.create(
            titre="Nouveau programme collectif", accroche="...", corps="...",
        )
        self.assertEqual(actu.slug, "nouveau-programme-collectif")


class ActualitesViewsTests(TestCase):
    def setUp(self):
        self.actu = Actualite.objects.create(
            titre="Résultats du challenge de juin", categorie="resultat",
            accroche="Bravo à tous les participants",
            corps="Contenu complet de l'article.",
            est_publiee=True,
        )

    def test_liste_actualites_200(self):
        resp = self.client.get(reverse("actualites:actualites"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Résultats du challenge de juin")

    def test_liste_ne_montre_pas_les_actualites_non_publiees(self):
        Actualite.objects.create(
            titre="Brouillon interne", accroche="...", corps="...", est_publiee=False,
        )
        resp = self.client.get(reverse("actualites:actualites"))
        self.assertNotContains(resp, "Brouillon interne")

    def test_detail_actualite_200(self):
        resp = self.client.get(reverse("actualites:actualite_detail", args=[self.actu.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Contenu complet de")

    def test_detail_actualite_non_publiee_404(self):
        brouillon = Actualite.objects.create(
            titre="Brouillon interne", accroche="...", corps="...", est_publiee=False,
        )
        resp = self.client.get(reverse("actualites:actualite_detail", args=[brouillon.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_actualite_inexistante_404(self):
        resp = self.client.get(reverse("actualites:actualite_detail", args=["inexistant"]))
        self.assertEqual(resp.status_code, 404)

