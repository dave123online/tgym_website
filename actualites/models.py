from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Actualite(models.Model):
    """
    Une actualité T-GYM (conseil, événement, résultat d'adhérent...).
    Outil de rétention : garde les adhérents engagés après leur inscription.
    Une actualité marquée "is_featured" alimente le bandeau "Top Body News",
    sur le même principe que l'Annonce (core) et le Programme phare (coaching).
    """

    CATEGORIE_CHOICES = [
        ("conseil", "Conseil"),
        ("evenement", "Événement"),
        ("resultat", "Résultat d'adhérent"),
        ("actu_salle", "Actu de la salle"),
    ]

    titre = models.CharField("Titre", max_length=150)
    slug = models.SlugField("Slug (URL)", max_length=160, unique=True, blank=True)
    categorie = models.CharField(
        "Catégorie", max_length=20, choices=CATEGORIE_CHOICES, default="conseil"
    )
    accroche = models.CharField(
        "Accroche courte", max_length=200,
        help_text="Résumé affiché dans la liste, avant l'ouverture de l'article.",
    )
    corps = models.TextField("Contenu")
    image = models.ImageField(
        "Image", upload_to="actualites/", null=True, blank=True,
        help_text="Optionnelle. Laisser vide si pas d'image.",
    )

    is_featured = models.BooleanField(
        "Mise en avant (Top Body News)", default=False,
        help_text="Alimente le bandeau 'Top Body News' affiché sur tout le site.",
    )
    est_publiee = models.BooleanField("Publiée (visible sur le site)", default=True)
    date_publication = models.DateTimeField("Date de publication", default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titre

    class Meta:
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
        ordering = ["-date_publication"]



