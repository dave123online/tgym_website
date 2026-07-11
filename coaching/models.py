from django.db import models
from django.utils.text import slugify


class Programme(models.Model):
    """
    Un programme phare (ex: "45 jours pour maigrir"). Pensé extensible :
    d'autres programmes pourront être ajoutés depuis l'admin sans toucher
    au code, chacun avec sa propre fiche.
    """
    titre = models.CharField("Titre", max_length=150)
    slug = models.SlugField("Slug (URL)", max_length=160, unique=True, blank=True)
    accroche = models.CharField(
        "Accroche courte", max_length=200,
        help_text="Ex: Un accompagnement intensif pour des résultats visibles et durables."
    )
    duree = models.CharField("Durée", max_length=50, help_text="Ex: 45 jours")
    objectif = models.TextField("Objectif", help_text="Ce que le programme vise à obtenir pour l'adhérent.")

    inclus = models.JSONField(
        "Ce qui est inclus", default=list, blank=True,
        help_text="Liste de points (ex: ['Suivi coach quotidien', 'Plan nutritionnel dédié'])",
    )

    prix_fcfa = models.PositiveIntegerField("Prix (FCFA)", null=True, blank=True, help_text="Laisser vide si inclus dans un abonnement existant.")
    prix_note = models.CharField(
        "Précision tarif", max_length=150, blank=True,
        help_text="Ex: 'Inclus dans l'abonnement Premium' ou 'Tarif dédié, hors abonnement'",
    )

    est_phare = models.BooleanField(
        "Programme phare", default=False,
        help_text="Mis en avant sur la page d'accueil et la méthode.",
    )
    actif = models.BooleanField("Actif (visible sur le site)", default=True)
    ordre_affichage = models.PositiveIntegerField("Ordre d'affichage", default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    class Meta:
        verbose_name = "Programme"
        verbose_name_plural = "Programmes"
        ordering = ["ordre_affichage", "titre"]



