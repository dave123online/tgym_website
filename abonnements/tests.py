from datetime import date, timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from abonnements.ia_relance import generer_message_relance
from abonnements.models import Abonnement, Plan, RelanceMessage
from abonnements.whatsapp_api import EnvoiWhatsAppIndisponible, envoyer_template_relance


class PlanModelTests(TestCase):
    def test_prix_affiche_formate_avec_separateur_de_milliers(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois")
        self.assertEqual(plan.prix_affiche(), "25.000 FCFA / mois")

    def test_str_contient_nom_et_prix(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois")
        self.assertIn("Premium", str(plan))


class AbonnementModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testclient", password="x")

    def test_date_fin_calculee_automatiquement_si_duree_definie(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        debut = date(2026, 1, 1)
        abo = Abonnement.objects.create(user=self.user, plan=plan, date_debut=debut)
        self.assertEqual(abo.date_fin, date(2026, 1, 31))

    def test_date_fin_calculee_ecrase_toute_saisie_manuelle(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        abo = Abonnement.objects.create(
            user=self.user, plan=plan, date_debut=date(2026, 1, 1),
            date_fin=date(2099, 1, 1),  # saisie manuelle volontairement absurde
        )
        self.assertEqual(abo.date_fin, date(2026, 1, 31))

    def test_date_fin_non_touchee_si_formule_sans_duree(self):
        plan = Plan.objects.create(nom="1 séance / semaine", prix_fcfa=5000, periode="", duree_jours=None)
        abo = Abonnement.objects.create(
            user=self.user, plan=plan, date_debut=date(2026, 1, 1), date_fin=None,
        )
        self.assertIsNone(abo.date_fin)

    def test_est_en_cours_true_pour_abonnement_actif_dans_la_fenetre(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        abo = Abonnement.objects.create(user=self.user, plan=plan, date_debut=date.today())
        self.assertTrue(abo.est_en_cours())

    def test_est_en_cours_false_si_inactif(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        abo = Abonnement.objects.create(user=self.user, plan=plan, date_debut=date.today(), actif=False)
        self.assertFalse(abo.est_en_cours())

    def test_est_en_cours_false_si_date_fin_passee(self):
        plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        abo = Abonnement.objects.create(user=self.user, plan=plan, date_debut=date.today() - timedelta(days=60))
        self.assertFalse(abo.est_en_cours())

    def test_jours_restants_none_si_pas_de_date_fin(self):
        plan = Plan.objects.create(nom="Flexible", prix_fcfa=5000, periode="", duree_jours=None)
        abo = Abonnement.objects.create(user=self.user, plan=plan, date_debut=date.today())
        self.assertIsNone(abo.jours_restants())


class IaRelanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="awa", password="x", first_name="Awa")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        self.abo = Abonnement.objects.create(
            user=self.user, plan=self.plan, date_debut=date.today() - timedelta(days=27),
        )

    @override_settings(GEMINI_API_KEY="")
    def test_sans_cle_api_utilise_le_message_de_secours(self):
        message, genere_par_ia = generer_message_relance(self.abo)
        self.assertFalse(genere_par_ia)
        self.assertIn("Awa", message)
        self.assertIn("Premium", message)

    @override_settings(GEMINI_API_KEY="fake-key")
    @patch("google.genai.Client")
    def test_avec_gemini_mocke_utilise_la_reponse_ia(self, mock_client_cls):
        mock_client = Mock()
        mock_client.models.generate_content.return_value = Mock(text="Salut Awa, pense à renouveler !")
        mock_client_cls.return_value = mock_client

        message, genere_par_ia = generer_message_relance(self.abo)
        self.assertTrue(genere_par_ia)
        self.assertEqual(message, "Salut Awa, pense à renouveler !")

    @override_settings(GEMINI_API_KEY="fake-key")
    @patch("google.genai.Client")
    def test_erreur_gemini_bascule_sur_le_secours_sans_exception(self, mock_client_cls):
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = RuntimeError("Gemini down")
        mock_client_cls.return_value = mock_client

        message, genere_par_ia = generer_message_relance(self.abo)
        self.assertFalse(genere_par_ia)
        self.assertIn("Awa", message)


class GenererRelancesCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="koffi", password="x", first_name="Koffi")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)

    @override_settings(GEMINI_API_KEY="")
    def test_genere_une_relance_pour_abonnement_expirant_bientot(self):
        Abonnement.objects.create(
            user=self.user, plan=self.plan,
            date_debut=date.today() - timedelta(days=28),  # expire dans 2 jours
        )
        out = StringIO()
        call_command("generer_relances", "--jours", "3", stdout=out)
        self.assertEqual(RelanceMessage.objects.count(), 1)
        self.assertIn("1 message(s)", out.getvalue())

    @override_settings(GEMINI_API_KEY="")
    def test_ignore_abonnement_hors_fenetre(self):
        Abonnement.objects.create(
            user=self.user, plan=self.plan,
            date_debut=date.today(),  # expire dans 30 jours, hors fenêtre de 3
        )
        call_command("generer_relances", "--jours", "3", stdout=StringIO())
        self.assertEqual(RelanceMessage.objects.count(), 0)

    @override_settings(GEMINI_API_KEY="")
    def test_idempotent_pas_de_doublon_sur_deuxieme_execution(self):
        Abonnement.objects.create(
            user=self.user, plan=self.plan,
            date_debut=date.today() - timedelta(days=28),
        )
        call_command("generer_relances", "--jours", "3", stdout=StringIO())
        call_command("generer_relances", "--jours", "3", stdout=StringIO())
        self.assertEqual(RelanceMessage.objects.count(), 1)


class WhatsappApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fatima", password="x", first_name="Fatima")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        self.abo = Abonnement.objects.create(
            user=self.user, plan=self.plan, date_debut=date.today() - timedelta(days=28),
        )
        # Profil créé automatiquement par le signal ; on renseigne le téléphone.
        self.user.profil.telephone = "94140535"
        self.user.profil.save(update_fields=["telephone"])

    @override_settings(WHATSAPP_ACCESS_TOKEN="", WHATSAPP_PHONE_NUMBER_ID="")
    def test_sans_credentials_leve_indisponible(self):
        with self.assertRaises(EnvoiWhatsAppIndisponible):
            envoyer_template_relance(self.abo)

    @override_settings(WHATSAPP_ACCESS_TOKEN="token-test", WHATSAPP_PHONE_NUMBER_ID="123456")
    def test_sans_telephone_leve_indisponible(self):
        self.user.profil.telephone = ""
        self.user.profil.save(update_fields=["telephone"])
        with self.assertRaises(EnvoiWhatsAppIndisponible):
            envoyer_template_relance(self.abo)

    @override_settings(WHATSAPP_ACCESS_TOKEN="token-test", WHATSAPP_PHONE_NUMBER_ID="123456")
    @patch("requests.post")
    def test_succes_renvoie_le_json_et_le_bon_payload(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"messages": [{"id": "wamid.abc"}]})

        resultat = envoyer_template_relance(self.abo)

        self.assertEqual(resultat, {"messages": [{"id": "wamid.abc"}]})
        appel = mock_post.call_args
        payload = appel.kwargs["json"]
        self.assertEqual(payload["to"], "22994140535")
        self.assertEqual(payload["template"]["name"], "relance_abonnement")
        parametres = payload["template"]["components"][0]["parameters"]
        self.assertEqual(parametres[0]["text"], "Fatima")
        self.assertEqual(parametres[1]["text"], "Premium")

    @override_settings(WHATSAPP_ACCESS_TOKEN="token-test", WHATSAPP_PHONE_NUMBER_ID="123456")
    @patch("requests.post")
    def test_echec_http_leve_indisponible_sans_crash(self, mock_post):
        mock_post.return_value = Mock(status_code=400, text="template inconnu")
        with self.assertRaises(EnvoiWhatsAppIndisponible):
            envoyer_template_relance(self.abo)


class EnvoyerRelancesWhatsappCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="issa", password="x", first_name="Issa")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)
        self.abo = Abonnement.objects.create(
            user=self.user, plan=self.plan, date_debut=date.today() - timedelta(days=28),
        )
        self.relance = RelanceMessage.objects.create(
            abonnement=self.abo, date_expiration_ciblee=self.abo.date_fin,
            contenu="Message de test",
        )

    @override_settings(WHATSAPP_ACCESS_TOKEN="", WHATSAPP_PHONE_NUMBER_ID="")
    def test_sans_credentials_message_reste_a_envoyer(self):
        call_command("envoyer_relances_whatsapp", stdout=StringIO())
        self.relance.refresh_from_db()
        self.assertEqual(self.relance.statut, RelanceMessage.Statut.A_ENVOYER)

    @override_settings(WHATSAPP_ACCESS_TOKEN="token-test", WHATSAPP_PHONE_NUMBER_ID="123456")
    @patch("requests.post")
    def test_succes_marque_le_message_envoye_automatiquement(self, mock_post):
        self.user.profil.telephone = "94140535"
        self.user.profil.save(update_fields=["telephone"])
        mock_post.return_value = Mock(status_code=200, json=lambda: {"messages": []})

        call_command("envoyer_relances_whatsapp", stdout=StringIO())

        self.relance.refresh_from_db()
        self.assertEqual(self.relance.statut, RelanceMessage.Statut.ENVOYE)
        self.assertTrue(self.relance.envoye_automatiquement)
        self.assertIsNotNone(self.relance.envoye_le)

