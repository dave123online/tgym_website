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
