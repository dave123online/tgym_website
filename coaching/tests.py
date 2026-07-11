from django.test import TestCase
from django.urls import reverse

from .models import Programme


class ProgrammeModelTests(TestCase):
    def test_slug_genere_automatiquement_depuis_le_titre(self):
        programme = Programme.objects.create(
            titre="45 jours pour maigrir", accroche="...", duree="45 jours", objectif="...",
        )
        self.assertEqual(programme.slug, "45-jours-pour-maigrir")

    def test_slug_manuel_est_respecte(self):
        programme = Programme.objects.create(
            titre="Un programme", slug="mon-slug-perso",
            accroche="...", duree="30 jours", objectif="...",
        )
        self.assertEqual(programme.slug, "mon-slug-perso")


class ProgrammesViewsTests(TestCase):
    def setUp(self):
        self.programme = Programme.objects.create(
            titre="45 jours pour maigrir", accroche="Résultats rapides",
            duree="45 jours", objectif="Perdre du poids durablement",
            inclus=["Suivi coach quotidien", "Plan nutritionnel évolutif"],
            est_phare=True, actif=True,
        )

    def test_liste_programmes_200(self):
        resp = self.client.get(reverse("coaching:programmes"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "45 jours pour maigrir")

    def test_liste_ne_montre_pas_les_programmes_inactifs(self):
        Programme.objects.create(
            titre="Programme caché", accroche="...", duree="10 jours",
            objectif="...", actif=False,
        )
        resp = self.client.get(reverse("coaching:programmes"))
        self.assertNotContains(resp, "Programme caché")

    def test_detail_programme_200(self):
        resp = self.client.get(
            reverse("coaching:programme_detail", args=[self.programme.slug])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Perdre du poids durablement")
        self.assertContains(resp, "Suivi coach quotidien")

    def test_detail_programme_inexistant_404(self):
        resp = self.client.get(reverse("coaching:programme_detail", args=["inexistant"]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_programme_inactif_404(self):
        inactif = Programme.objects.create(
            titre="Programme caché", accroche="...", duree="10 jours",
            objectif="...", actif=False,
        )
        resp = self.client.get(reverse("coaching:programme_detail", args=[inactif.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_detail_contient_lien_whatsapp_contextualise(self):
        resp = self.client.get(
            reverse("coaching:programme_detail", args=[self.programme.slug])
        )
        self.assertContains(resp, "wa.me")

