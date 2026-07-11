from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from abonnements.models import Abonnement, Plan

from .decorators import role_required
from .forms import generer_mot_de_passe, generer_username
from .models import Profil
from .utils import normaliser_telephone


class ProfilSignalTests(TestCase):
    def test_superuser_recoit_le_role_staff(self):
        user = User.objects.create_superuser(username="boss", password="x", email="boss@tgym.local")
        self.assertTrue(hasattr(user, "profil"))
        self.assertEqual(user.profil.role, Profil.Role.STAFF)

    def test_user_staff_recoit_le_role_staff(self):
        user = User.objects.create_user(username="employe", password="x", is_staff=True)
        self.assertEqual(user.profil.role, Profil.Role.STAFF)

    def test_user_normal_recoit_le_role_adherent_par_defaut(self):
        user = User.objects.create_user(username="client", password="x")
        self.assertEqual(user.profil.role, Profil.Role.ADHERENT)

    def test_pas_de_doublon_de_profil_a_chaque_save(self):
        user = User.objects.create_user(username="client2", password="x")
        user.first_name = "Modifié"
        user.save()
        self.assertEqual(Profil.objects.filter(user=user).count(), 1)


class NormaliserTelephoneTests(TestCase):
    def test_retire_prefixe_00229(self):
        self.assertEqual(normaliser_telephone("00229 94140535"), "94140535")

    def test_retire_prefixe_plus229(self):
        self.assertEqual(normaliser_telephone("+229 94140535"), "94140535")

    def test_retire_prefixe_229(self):
        self.assertEqual(normaliser_telephone("22994140535"), "94140535")

    def test_numero_local_inchange(self):
        self.assertEqual(normaliser_telephone("94140535"), "94140535")

    def test_retire_les_espaces(self):
        self.assertEqual(normaliser_telephone("94 14 05 35"), "94140535")


class IdentifiantOuTelephoneBackendTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # évite la contamination par le compteur anti-bruteforce
        self.user = User.objects.create_user(username="awakoffi", password="MotDePasse123")
        self.user.profil.telephone = "94140535"
        self.user.profil.save(update_fields=["telephone"])

    def test_connexion_par_username(self):
        ok = self.client.login(username="awakoffi", password="MotDePasse123")
        self.assertTrue(ok)

    def test_connexion_par_telephone_local(self):
        ok = self.client.login(username="94140535", password="MotDePasse123")
        self.assertTrue(ok)

    def test_connexion_par_telephone_prefixe_229(self):
        ok = self.client.login(username="22994140535", password="MotDePasse123")
        self.assertTrue(ok)

    def test_connexion_par_telephone_prefixe_plus229(self):
        ok = self.client.login(username="+22994140535", password="MotDePasse123")
        self.assertTrue(ok)

    def test_mauvais_mot_de_passe_refuse(self):
        ok = self.client.login(username="awakoffi", password="mauvais")
        self.assertFalse(ok)

    def test_identifiant_inexistant_refuse(self):
        ok = self.client.login(username="personne_ici", password="MotDePasse123")
        self.assertFalse(ok)

    def test_vue_connexion_fonctionnelle_via_le_formulaire(self):
        resp = self.client.post(reverse("comptes:connexion"), {
            "username": "awakoffi", "password": "MotDePasse123",
        })
        self.assertRedirects(resp, reverse("comptes:mon_espace"))

    def test_un_seul_backend_actif(self):
        # Audit sécurité 09/07/2026, finding #3 : ModelBackend ne doit plus
        # être présent à côté de IdentifiantOuTelephoneBackend, sans quoi un
        # identifiant existant déclenche deux hash (un par backend) contre
        # un seul pour un identifiant inexistant — canal de timing exploitable
        # à distance pour énumérer les comptes.
        from django.conf import settings
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            ["comptes.backends.IdentifiantOuTelephoneBackend"],
        )

    def test_hash_factice_sur_identifiant_inconnu(self):
        # Le correctif fait un vrai hash (réel ou factice) dans TOUS les cas
        # pour égaliser le coût CPU. On ne peut pas fiabiliser un test sur un
        # écart de millisecondes en CI, donc on vérifie le mécanisme : un
        # hash factice est bien déclenché (User().set_password appelé) sur
        # le chemin "utilisateur introuvable".
        from unittest.mock import patch

        from comptes.backends import IdentifiantOuTelephoneBackend

        backend = IdentifiantOuTelephoneBackend()
        with patch(
            "comptes.backends.User.set_password", autospec=True
        ) as mock_set_password:
            resultat = backend.authenticate(
                request=None, username="personne_ici", password="peu importe",
            )
        self.assertIsNone(resultat)
        mock_set_password.assert_called_once()


class RoleRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staffuser", password="x", is_staff=True)
        self.adherent = User.objects.create_user(username="clientuser", password="x")

    def test_anonyme_redirige_vers_connexion(self):
        resp = self.client.get(reverse("comptes:creer_compte_adherent"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("comptes:connexion"), resp.url)

    def test_adherent_recoit_403(self):
        self.client.login(username="clientuser", password="x")
        resp = self.client.get(reverse("comptes:creer_compte_adherent"))
        self.assertEqual(resp.status_code, 403)

    def test_staff_peut_acceder(self):
        self.client.login(username="staffuser", password="x")
        resp = self.client.get(reverse("comptes:creer_compte_adherent"))
        self.assertEqual(resp.status_code, 200)


class CreationCompteAdherentHelpersTests(TestCase):
    def test_generer_mot_de_passe_longueur_par_defaut(self):
        mdp = generer_mot_de_passe()
        self.assertEqual(len(mdp), 10)

    def test_generer_mot_de_passe_evite_caracteres_ambigus(self):
        mdp = generer_mot_de_passe(longueur=200)
        for caractere_ambigu in "0O1lI":
            self.assertNotIn(caractere_ambigu, mdp)

    def test_generer_username_slugifie_le_nom(self):
        username = generer_username("Awa Koffi")
        self.assertEqual(username, "awakoffi")

    def test_generer_username_ajoute_un_suffixe_si_deja_pris(self):
        User.objects.create_user(username="awakoffi", password="x")
        username = generer_username("Awa Koffi")
        self.assertEqual(username, "awakoffi2")


class CreerCompteAdherentViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staffuser", password="x", is_staff=True)
        self.client.login(username="staffuser", password="x")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)

    def test_creation_reussie_cree_user_profil_et_abonnement(self):
        resp = self.client.post(reverse("comptes:creer_compte_adherent"), {
            "nom_complet": "Issa Boni", "telephone": "94140535", "plan": self.plan.pk,
        })
        self.assertEqual(resp.status_code, 302)

        user = User.objects.get(username="issaboni")
        self.assertEqual(user.profil.role, Profil.Role.ADHERENT)
        self.assertEqual(user.profil.telephone, "94140535")
        self.assertTrue(Abonnement.objects.filter(user=user, plan=self.plan).exists())

    def test_identifiants_affiches_une_seule_fois(self):
        self.client.post(reverse("comptes:creer_compte_adherent"), {
            "nom_complet": "Fatima Alassane", "telephone": "63404995", "plan": "",
        })
        # Premier GET après création : les identifiants doivent être affichés
        resp1 = self.client.get(reverse("comptes:creer_compte_adherent"))
        self.assertContains(resp1, "fatimaalassane")
        # Deuxième GET : ils ne doivent plus apparaître (pop une seule fois)
        resp2 = self.client.get(reverse("comptes:creer_compte_adherent"))
        self.assertNotContains(resp2, "fatimaalassane")

    def test_sans_plan_aucun_abonnement_cree(self):
        self.client.post(reverse("comptes:creer_compte_adherent"), {
            "nom_complet": "Client Sans Plan", "telephone": "94140535", "plan": "",
        })
        user = User.objects.get(username="clientsansplan")
        self.assertFalse(Abonnement.objects.filter(user=user).exists())


class MonEspaceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="adherent1", password="x")
        self.plan = Plan.objects.create(nom="Premium", prix_fcfa=25000, periode="/ mois", duree_jours=30)

    def test_anonyme_redirige_vers_connexion(self):
        resp = self.client.get(reverse("comptes:mon_espace"))
        self.assertEqual(resp.status_code, 302)

    def test_adherent_sans_abonnement_voit_la_page(self):
        self.client.login(username="adherent1", password="x")
        resp = self.client.get(reverse("comptes:mon_espace"))
        self.assertEqual(resp.status_code, 200)

    def test_abonnement_en_cours_affiche(self):
        from datetime import date
        Abonnement.objects.create(user=self.user, plan=self.plan, date_debut=date.today())
        self.client.login(username="adherent1", password="x")
        resp = self.client.get(reverse("comptes:mon_espace"))
        self.assertContains(resp, "Premium")

    def test_un_utilisateur_ne_voit_pas_labonnement_dun_autre(self):
        # Vérifie l'absence d'IDOR : chaque adhérent ne voit que le sien.
        from datetime import date
        autre_user = User.objects.create_user(username="adherent2", password="x")
        Abonnement.objects.create(user=autre_user, plan=self.plan, date_debut=date.today())

        self.client.login(username="adherent1", password="x")
        resp = self.client.get(reverse("comptes:mon_espace"))
        self.assertIsNone(resp.context["abonnement_actif"])


class AntiBruteForceMiddlewareTests(TestCase):
    """
    Audit sécurité 09/07/2026, finding #6 (backlog). Vérifie le
    verrouillage par IP sur /connexion/ ET /admin/login/ après le seuil de
    tentatives échouées — ainsi que le fait qu'un succès réinitialise le
    compteur, pour ne jamais bloquer un utilisateur légitime après une
    simple faute de frappe suivie du bon mot de passe.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(
            username="staffuser", password="BonMotDePasse123",
            is_staff=True, is_superuser=True,
        )

    def _echec(self, chemin="/connexion/"):
        return self.client.post(chemin, {"username": "staffuser", "password": "faux"})

    def test_verrouillage_apres_le_seuil_sur_connexion(self):
        from comptes.middleware import SEUIL_TENTATIVES

        for _ in range(SEUIL_TENTATIVES):
            resp = self._echec()
            self.assertNotEqual(resp.status_code, 429)

        resp = self._echec()
        self.assertEqual(resp.status_code, 429)

    def test_verrouillage_partage_entre_connexion_et_admin_login(self):
        # Même IP -> même compteur, peu importe par quelle porte on frappe.
        from comptes.middleware import SEUIL_TENTATIVES

        for _ in range(SEUIL_TENTATIVES):
            self._echec("/connexion/")

        resp = self.client.post(
            "/admin/login/", {"username": "staffuser", "password": "faux"}
        )
        self.assertEqual(resp.status_code, 429)

    def test_une_connexion_reussie_reinitialise_le_compteur(self):
        for _ in range(5):
            self._echec()

        resp_ok = self.client.post(
            "/connexion/", {"username": "staffuser", "password": "BonMotDePasse123"}
        )
        self.assertEqual(resp_ok.status_code, 302)

        # Après un succès, 5 nouveaux échecs ne doivent PAS suffire à
        # eux seuls à déclencher le verrouillage (le compteur est reparti
        # de zéro, pas resté à 5).
        for _ in range(5):
            resp = self._echec()
            self.assertNotEqual(resp.status_code, 429)

    def test_utilisateur_different_meme_ip_est_aussi_concerne(self):
        # Le compteur est par IP, pas par identifiant ciblé : un attaquant
        # ne peut pas contourner le verrouillage en changeant de username.
        from comptes.middleware import SEUIL_TENTATIVES

        for _ in range(SEUIL_TENTATIVES):
            self.client.post("/connexion/", {"username": "nimporte_qui", "password": "faux"})

        resp = self._echec()
        self.assertEqual(resp.status_code, 429)

