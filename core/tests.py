import json
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from abonnements.models import Plan
from coaching.models import Programme
from core.models import Annonce, SiteConfig
from core.whatsapp import (
    build_generic_whatsapp_link,
    build_plan_whatsapp_link,
    build_whatsapp_link,
    numero_international,
)


class SiteConfigModelTests(TestCase):
    def test_get_solo_cree_une_seule_ligne(self):
        config1 = SiteConfig.get_solo()
        config2 = SiteConfig.get_solo()
        self.assertEqual(config1.pk, config2.pk)
        self.assertEqual(SiteConfig.objects.count(), 1)

    def test_impossible_de_creer_une_deuxieme_config(self):
        SiteConfig.get_solo()
        with self.assertRaises(Exception):
            SiteConfig.objects.create(nom="Autre salle")

    def test_google_maps_url_fallback_sur_adresse_si_pas_de_gps(self):
        config = SiteConfig.get_solo()
        config.latitude = None
        config.longitude = None
        config.adresse_zone = "Abomey-Calavi, tronçon Carrefour TOKAN - Carrefour HOUÈTÔ"
        url = config.google_maps_url()
        self.assertIn("google.com/maps/search", url)
        self.assertIn("Abomey-Calavi", url)

    def test_google_maps_url_utilise_les_coordonnees_gps_si_presentes(self):
        config = SiteConfig.get_solo()
        config.latitude = 6.4483
        config.longitude = 2.3548
        url = config.google_maps_url()
        self.assertIn("6.4483", url)
        self.assertIn("2.3548", url)


class AnnonceModelTests(TestCase):
    def test_annonce_active_sans_dates_est_visible(self):
        annonce = Annonce.objects.create(message="Promo", actif=True)
        self.assertTrue(annonce.est_visible())

    def test_annonce_inactive_nest_jamais_visible(self):
        annonce = Annonce.objects.create(message="Promo", actif=False)
        self.assertFalse(annonce.est_visible())

    def test_annonce_pas_encore_commencee_nest_pas_visible(self):
        annonce = Annonce.objects.create(
            message="Promo future", actif=True,
            date_debut=timezone.now() + timedelta(days=1),
        )
        self.assertFalse(annonce.est_visible())

    def test_annonce_expiree_nest_pas_visible(self):
        annonce = Annonce.objects.create(
            message="Promo passée", actif=True,
            date_debut=timezone.now() - timedelta(days=10),
            date_fin=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(annonce.est_visible())


class WhatsappLinkBuilderTests(TestCase):
    def test_numero_international_ajoute_le_prefixe_229(self):
        self.assertEqual(numero_international("94140535"), "22994140535")

    def test_numero_international_conserve_prefixe_deja_present(self):
        self.assertEqual(numero_international("22994140535"), "22994140535")

    def test_numero_international_retire_le_plus(self):
        self.assertEqual(numero_international("+22994140535"), "22994140535")

    def test_numero_international_retire_les_espaces(self):
        self.assertEqual(numero_international("94 14 05 35"), "22994140535")

    def test_build_whatsapp_link_encode_le_message(self):
        lien = build_whatsapp_link("Bonjour, ça va ?", numero="94140535")
        self.assertTrue(lien.startswith("https://wa.me/22994140535?text="))
        self.assertIn("Bonjour", lien)

    def test_build_generic_whatsapp_link_avec_sujet(self):
        lien = build_generic_whatsapp_link("la méthode T-GYM")
        self.assertIn("wa.me", lien)
        self.assertIn("m%C3%A9thode", lien)  # "méthode" encodé

    def test_build_generic_whatsapp_link_sans_sujet(self):
        lien = build_generic_whatsapp_link()
        self.assertIn("wa.me", lien)

    def test_build_plan_whatsapp_link_contient_le_nom_et_prix(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois")
        lien = build_plan_whatsapp_link(plan)
        self.assertIn("wa.me", lien)
        self.assertIn("Premium", lien)


class PagesPubliquesTests(TestCase):
    """Pages qui ne doivent jamais casser (Phase 1 + 1.5 + 2)."""

    def test_accueil_200(self):
        resp = self.client.get(reverse("core:accueil"))
        self.assertEqual(resp.status_code, 200)

    def test_methode_200(self):
        resp = self.client.get(reverse("core:methode"))
        self.assertEqual(resp.status_code, 200)

    def test_tarifs_200(self):
        resp = self.client.get(reverse("core:tarifs"))
        self.assertEqual(resp.status_code, 200)

    def test_ou_nous_trouver_200(self):
        resp = self.client.get(reverse("core:ou_nous_trouver"))
        self.assertEqual(resp.status_code, 200)

    def test_accueil_affiche_le_plan_populaire(self):
        Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", is_populaire=True, actif=True)
        resp = self.client.get(reverse("core:accueil"))
        self.assertContains(resp, "Premium")

    def test_accueil_affiche_le_programme_phare(self):
        Programme.objects.create(
            titre="45 jours pour maigrir", accroche="Résultats rapides",
            duree="45 jours", objectif="Perdre du poids", est_phare=True, actif=True,
        )
        resp = self.client.get(reverse("core:accueil"))
        self.assertContains(resp, "45 jours pour maigrir")

    def test_bandeau_annonce_prioritaire_sur_actualite_phare(self):
        from actualites.models import Actualite

        Annonce.objects.create(message="Promo du bandeau", actif=True)
        Actualite.objects.create(
            titre="Une actu vedette", accroche="...", corps="...",
            is_featured=True, est_publiee=True,
        )
        resp = self.client.get(reverse("core:accueil"))
        self.assertContains(resp, "Promo du bandeau")
        self.assertNotContains(resp, "Top Body News")

    def test_bandeau_actualite_phare_si_pas_dannonce_active(self):
        from actualites.models import Actualite

        Actualite.objects.create(
            titre="Une actu vedette", accroche="...", corps="...",
            is_featured=True, est_publiee=True,
        )
        resp = self.client.get(reverse("core:accueil"))
        self.assertContains(resp, "Top Body News")
        self.assertContains(resp, "Une actu vedette")


class ChatbotMessageViewTests(TestCase):
    def setUp(self):
        self.url = reverse("core:chatbot_message")
        # Le throttle IP (core/views.py::_limite_ip_atteinte, ajouté suite à
        # l'audit sécurité du 09/07/2026) vit dans le cache Django, qui
        # n'est PAS réinitialisé automatiquement entre les tests comme la
        # base de test l'est. Sans ce clear(), un test qui épuise la limite
        # contaminerait les suivants dans la même exécution.
        cache.clear()

    def _post(self, message):
        return self.client.post(
            self.url, data=json.dumps({"message": message}),
            content_type="application/json",
        )

    def test_get_refuse_405(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)

    def test_message_vide_refuse_400(self):
        resp = self._post("")
        self.assertEqual(resp.status_code, 400)

    def test_corps_non_json_refuse_400(self):
        resp = self.client.post(self.url, data="pas du json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    @override_settings(GEMINI_API_KEY="")
    def test_sans_cle_api_renvoie_le_message_de_repli(self):
        resp = self._post("Bonjour, vous êtes ouverts le dimanche ?")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("WhatsApp", data["reponse"])

    @override_settings(GEMINI_API_KEY="")
    def test_limite_journaliere_atteinte_au_21e_message(self):
        # Même session (même client) réutilisée à chaque appel -> le compteur
        # en session doit s'incrémenter normalement (comportement voulu,
        # même si contournable par rotation de session — voir PROGRESS.md).
        for _ in range(20):
            resp = self._post("test")
            self.assertNotIn("limite_atteinte", resp.json())
        resp_21 = self._post("test de trop")
        data = resp_21.json()
        self.assertTrue(data.get("limite_atteinte"))

    @override_settings(GEMINI_API_KEY="")
    def test_message_trop_long_est_tronque_sans_erreur(self):
        resp = self._post("a" * 1000)
        self.assertEqual(resp.status_code, 200)

    @override_settings(GEMINI_API_KEY="fake-key-pour-le-test")
    @patch("core.views.obtenir_reponse")
    def test_reponse_gemini_mockee_est_bien_renvoyee(self, mock_obtenir_reponse):
        mock_obtenir_reponse.return_value = "Réponse générée par Gemini (mock)."
        resp = self._post("Quels sont vos tarifs ?")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["reponse"], "Réponse générée par Gemini (mock).")

    @override_settings(GEMINI_API_KEY="")
    def test_limite_par_ip_resiste_a_un_nouveau_client_sans_cookies(self):
        # Audit sécurité 09/07/2026, finding #4 : avant correctif, un script
        # qui ignore les cookies de session contournait totalement la limite
        # (25/25 passaient). On simule ici exactement ce scénario : chaque
        # requête utilise un NOUVEAU client Django (donc une nouvelle
        # session), mais la même IP de test (REMOTE_ADDR par défaut du
        # client de test). Le throttle par IP doit quand même se déclencher.
        from django.test import Client

        for _ in range(20):
            resp = Client().post(
                self.url, data=json.dumps({"message": "test"}),
                content_type="application/json",
            )
            self.assertNotIn("limite_atteinte", resp.json())

        resp_21 = Client().post(
            self.url, data=json.dumps({"message": "test de trop"}),
            content_type="application/json",
        )
        self.assertTrue(resp_21.json().get("limite_atteinte"))

    @override_settings(GEMINI_API_KEY="")
    def test_limite_par_ip_respecte_x_forwarded_for(self):
        # Deux IP différentes (via X-Forwarded-For, comme derrière Render)
        # doivent avoir des compteurs indépendants. Client Django distinct à
        # chaque requête pour isoler du compteur de session (test dédié au
        # compteur IP, pas à celui de session).
        from django.test import Client

        for _ in range(20):
            resp = Client().post(
                self.url, data=json.dumps({"message": "test"}),
                content_type="application/json",
                HTTP_X_FORWARDED_FOR="41.138.10.10",
            )
            self.assertNotIn("limite_atteinte", resp.json())

        resp_autre_ip = Client().post(
            self.url, data=json.dumps({"message": "toujours ok"}),
            content_type="application/json",
            HTTP_X_FORWARDED_FOR="41.138.10.99",
        )
        self.assertNotIn("limite_atteinte", resp_autre_ip.json())

