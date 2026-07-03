from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SiteConfig(models.Model):
    """
    Configuration globale du site (singleton — une seule ligne en base).
    Modifiable depuis l'admin sans toucher au code : contacts, horaires, réseaux.
    """
    nom = models.CharField("Nom de la salle", max_length=100, default="T-GYM")
    slogan = models.CharField("Slogan", max_length=200, default="La référence du sport.")

    horaires_texte = models.CharField(
        "Horaires (affichage)",
        max_length=150,
        default="Ouvert 7j/7 (du Lundi au Dimanche) de 07h00 à 21h00",
    )

    whatsapp_numero_1 = models.CharField("Numéro WhatsApp #1", max_length=20, default="94140535")
    whatsapp_numero_2 = models.CharField("Numéro WhatsApp #2", max_length=20, default="63404995")

    facebook_url = models.URLField("Lien page Facebook", blank=True, default="https://facebook.com/tgymbenin")

    adresse_zone = models.CharField(
        "Zone", max_length=150, default="Abomey-Calavi, tronçon Carrefour TOKAN - Carrefour HOUÈTÔ"
    )
    adresse_reperes = models.CharField(
        "Repères de direction",
        max_length=255,
        default="À gauche en quittant le carrefour Tokan, ou à droite en quittant le carrefour Houètô.",
    )
    latitude = models.DecimalField(
        "Latitude GPS", max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Ex: 6.4483. Laisser vide si inconnu — le lien Maps utilisera l'adresse texte à la place.",
    )
    longitude = models.DecimalField(
        "Longitude GPS", max_digits=10, decimal_places=7, null=True, blank=True,
        help_text="Ex: 2.3548",
    )

    def google_maps_url(self) -> str:
        """
        Lien direct vers Google Maps — pas d'API, pas de clé, pas de
        permission de géolocalisation demandée au visiteur. Un clic
        ouvre Maps avec le point exact (ou l'adresse en fallback).
        """
        if self.latitude is not None and self.longitude is not None:
            query = f"{self.latitude},{self.longitude}"
        else:
            query = f"{self.nom} {self.adresse_zone}"
        from urllib.parse import quote
        return f"https://www.google.com/maps/search/?api=1&query={quote(str(query))}"

    def clean(self):
        # Empêche la création d'une deuxième ligne (pattern singleton)
        if not self.pk and SiteConfig.objects.exists():
            raise ValidationError("Une configuration du site existe déjà. Modifiez-la plutôt que d'en créer une nouvelle.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Configuration — {self.nom}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = "Configuration du site"
        verbose_name_plural = "Configuration du site"


class Annonce(models.Model):
    """
    Bandeau coulissant ("Top Body"). Le staff peut publier/dépublier une actu,
    un changement d'horaire ou une promo flash sans toucher au code.
    """
    message = models.CharField("Message", max_length=200)
    lien = models.URLField("Lien (optionnel)", blank=True)
    actif = models.BooleanField("Actif", default=True)
    date_debut = models.DateTimeField("Début d'affichage", default=timezone.now)
    date_fin = models.DateTimeField("Fin d'affichage", null=True, blank=True)

    def est_visible(self):
        if not self.actif:
            return False
        now = timezone.now()
        if self.date_debut and now < self.date_debut:
            return False
        if self.date_fin and now > self.date_fin:
            return False
        return True

    def __str__(self):
        return self.message

    class Meta:
        verbose_name = "Annonce (bandeau)"
        verbose_name_plural = "Annonces (bandeau)"
        ordering = ["-date_debut"]
