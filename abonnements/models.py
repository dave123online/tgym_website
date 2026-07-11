from datetime import date, timedelta

from django.conf import settings
from django.db import models


class Plan(models.Model):
    """
    Une formule tarifaire T-GYM (Premium mensuel ou formule flexible).
    Modèle volontairement simple : pas de tailles, pas de multi-devise —
    une salle de sport a une poignée de formules, pas un catalogue.
    """

    class Categorie(models.TextChoices):
        PREMIUM = "premium", "Abonnement Standard (Premium)"
        FLEXIBLE = "flexible", "Formule flexible (à la carte)"

    nom = models.CharField("Nom de la formule", max_length=100)
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=Categorie.choices, default=Categorie.FLEXIBLE
    )
    prix_fcfa = models.PositiveIntegerField("Prix (FCFA)")
    periode = models.CharField(
        "Période", max_length=50, help_text="Ex: /mois, pour 14 séances/mois, /semaine"
    )
    duree_jours = models.PositiveIntegerField(
        "Durée (jours)", null=True, blank=True,
        help_text="Utilisée pour calculer automatiquement la date de fin d'un abonnement "
                   "(ex: 30 pour un mensuel). Laisser vide pour les formules sans durée "
                   "calculable (ex: à la carte) — la date de fin restera alors saisie manuellement.",
    )
    description_courte = models.CharField(
        "Description courte", max_length=150, blank=True,
        help_text="Ex: '14 séances dans le mois'"
    )
    inclus = models.JSONField(
        "Éléments inclus", default=list, blank=True,
        help_text="Liste de points affichés sous forme de checklist (ex: ['Accès salle', 'Suivi coach permanent'])",
    )
    is_populaire = models.BooleanField(
        "Mettre en avant", default=False,
        help_text="Affiche cette formule comme le choix recommandé sur la grille tarifaire."
    )
    actif = models.BooleanField("Actif (visible sur le site)", default=True)
    ordre_affichage = models.PositiveIntegerField("Ordre d'affichage", default=0)

    def prix_affiche(self) -> str:
        return f"{self.prix_fcfa:,} FCFA {self.periode}".replace(",", ".")

    def __str__(self):
        return f"{self.nom} — {self.prix_affiche()}"

    class Meta:
        verbose_name = "Formule tarifaire"
        verbose_name_plural = "Formules tarifaires"
        ordering = ["ordre_affichage", "prix_fcfa"]


class Abonnement(models.Model):
    """
    Souscription d'un user à une formule (Plan), avec historique.

    Un user peut avoir plusieurs Abonnement dans le temps (renouvellements,
    changements de formule). `actif` + `est_en_cours()` permettent de
    retrouver rapidement l'abonnement courant sans supprimer l'historique.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="abonnements", verbose_name="Adhérent",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT,
        related_name="abonnements", verbose_name="Formule",
    )
    date_debut = models.DateField("Date de début", default=date.today)
    date_fin = models.DateField(
        "Date de fin", null=True, blank=True,
        help_text="Calculée automatiquement si la formule a une durée définie (écrase la saisie "
                   "manuelle à chaque enregistrement). Sinon, à renseigner à la main.",
    )
    actif = models.BooleanField(
        "Actif", default=True,
        help_text="Décoche pour clore/annuler cet abonnement sans le supprimer.",
    )
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    def save(self, *args, **kwargs):
        # Si la formule a une durée définie, la date de fin est toujours
        # recalculée depuis date_debut + duree_jours (écrase toute saisie
        # manuelle). Sinon (formule "à la carte" sans duree_jours), on ne
        # touche pas à date_fin — laissée à la main du staff.
        if self.plan_id and self.plan.duree_jours is not None:
            self.date_fin = self.date_debut + timedelta(days=self.plan.duree_jours)
        super().save(*args, **kwargs)

    def est_en_cours(self) -> bool:
        if not self.actif:
            return False
        if self.date_fin and self.date_fin < date.today():
            return False
        return self.date_debut <= date.today()

    est_en_cours.boolean = True
    est_en_cours.short_description = "En cours"

    def jours_restants(self):
        """Nombre de jours avant expiration, ou None si pas de date_fin définie."""
        if not self.date_fin:
            return None
        return (self.date_fin - date.today()).days

    def __str__(self):
        return f"{self.user.get_username()} — {self.plan.nom} ({self.date_debut})"

    class Meta:
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"
        ordering = ["-date_debut", "-date_creation"]


class RelanceMessage(models.Model):
    """
    Message de relance généré (via IA) pour un abonnement qui arrive à
    expiration. Tant que l'Étape 4 (API WhatsApp Business) n'est pas
    branchée, ces messages restent au statut A_ENVOYER : le staff les
    consulte dans l'admin et les copie manuellement vers WhatsApp.
    """

    class Statut(models.TextChoices):
        A_ENVOYER = "a_envoyer", "À envoyer (copier manuellement)"
        ENVOYE = "envoye", "Envoyé"
        IGNORE = "ignore", "Ignoré"

    abonnement = models.ForeignKey(
        Abonnement, on_delete=models.CASCADE,
        related_name="relances", verbose_name="Abonnement",
    )
    date_expiration_ciblee = models.DateField(
        "Date d'expiration ciblée",
        help_text="Copie de la date de fin de l'abonnement au moment de la génération — "
                   "sert à éviter de régénérer un message pour la même échéance.",
    )
    contenu = models.TextField("Message généré")
    genere_par_ia = models.BooleanField(
        "Généré par l'IA", default=True,
        help_text="Décoché si l'IA était indisponible au moment de la génération "
                   "et qu'un message de secours (gabarit fixe) a été utilisé à la place.",
    )
    statut = models.CharField(
        "Statut", max_length=20, choices=Statut.choices, default=Statut.A_ENVOYER,
    )
    date_generation = models.DateTimeField("Généré le", auto_now_add=True)
    envoye_le = models.DateTimeField("Envoyé le", null=True, blank=True)
    envoye_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="relances_envoyees", verbose_name="Envoyé par",
        help_text="Membre du staff qui a envoyé le message manuellement. "
                   "Vide si l'envoi a été automatique (voir « Envoyé automatiquement »).",
    )
    envoye_automatiquement = models.BooleanField(
        "Envoyé automatiquement", default=False,
        help_text="Coché si envoyé via l'API WhatsApp Business (Étape 4), "
                   "décoché si envoyé/à envoyer manuellement par le staff.",
    )

    def __str__(self):
        return f"Relance {self.abonnement} — {self.get_statut_display()}"

    class Meta:
        verbose_name = "Message de relance"
        verbose_name_plural = "Messages de relance"
        ordering = ["-date_generation"]



