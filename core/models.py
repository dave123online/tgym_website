from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# django-cloudinary-storage utilise resource_type="image" par défaut sur
# MediaCloudinaryStorage — correct pour ImageField, mais Cloudinary refuse
# un .mp4 envoyé avec ce type ("Invalid image file"). Les champs vidéo
# doivent explicitement utiliser resource_type="video".
video_storage = MediaCloudinaryStorage(resource_type="video")


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
    instagram_url = models.URLField("Lien page Instagram", blank=True, default="")

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

    hero_image = models.ImageField(
        "Photo de fond (accueil)", upload_to="site/", null=True, blank=True,
        help_text="Photo large de la salle affichée derrière le titre de l'accueil. "
                   "Idéalement une photo prise en salle, ambiance/lumière (1600px de large minimum).",
    )
    hero_video = models.FileField(
        "Vidéo de fond (accueil, optionnel)", upload_to="site/", null=True, blank=True,
        storage=video_storage,
        help_text="Courte vidéo (10-20s, en boucle, sans son) de l'ambiance de la salle. "
                   "Si renseignée, prend le pas sur la photo de fond. Fichier léger recommandé (<10 Mo).",
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


class VideoSalle(models.Model):
    """
    Vidéos courtes de la salle, affichées sur l'accueil (et, pour les
    généralistes, sur /tarifs/ aussi). Trois usages :
    - non liée à un programme : "généraliste" (ambiance, matériel, salle),
      affichée dans le mur vidéo (accueil ET tarifs) ;
    - liée à un programme, type "activité" : clips d'exercice/séance,
      affichés en ligne compacte dans la section du programme phare ;
    - liée à un programme, type "témoignage" : clips d'adhérents coupés
      dans les passages intéressants, affichés dans le carrousel
      "témoignages" (une vidéo à la fois, avec le son) de la section du
      programme phare.
    Comme PhotoSalle : sections masquées automatiquement tant qu'aucune
    vidéo n'est en ligne, pas de placeholder cassé avant upload.
    """

    class TypeVideo(models.TextChoices):
        GENERALE = "generale", "Généraliste (pas de programme)"
        ACTIVITE = "activite", "Activité (programme)"
        TEMOIGNAGE = "temoignage", "Témoignage (programme)"

    fichier = models.FileField(
        "Fichier vidéo", upload_to="videos/",
        storage=video_storage,
        help_text="Format vertical ou horizontal, les deux fonctionnent. "
                   "Fichier léger recommandé (idéalement <15 Mo, sans son "
                   "nécessaire — elle sera lue en muet/boucle, sauf en "
                   "carrousel témoignages où le son est utilisé).",
    )
    apercu = models.ImageField(
        "Image d'aperçu (poster)", upload_to="videos/apercus/", null=True, blank=True,
        help_text="Image affichée le temps que la vidéo charge. Optionnelle mais recommandée.",
    )
    legende = models.CharField("Légende (optionnelle)", max_length=150, blank=True)
    programme = models.ForeignKey(
        "coaching.Programme", verbose_name="Programme associé (optionnel)",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="videos",
        help_text="Laisser vide pour une vidéo généraliste (mur accueil + tarifs). "
                   "Renseigner pour une vidéo liée à un programme (voir le champ Type).",
    )
    type_video = models.CharField(
        "Type", max_length=20, choices=TypeVideo.choices, default=TypeVideo.GENERALE,
        help_text="Ignoré si aucun programme n'est renseigné (repasse automatiquement "
                   "à 'Généraliste' à l'enregistrement dans ce cas).",
    )
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre_affichage = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_ajout = models.DateTimeField("Ajoutée le", default=timezone.now)

    def save(self, *args, **kwargs):
        # Cohérence automatique : une vidéo sans programme est forcément
        # "généraliste", quel que soit ce qui a été sélectionné par erreur.
        if self.programme_id is None:
            self.type_video = self.TypeVideo.GENERALE
        super().save(*args, **kwargs)

    def __str__(self):
        return self.legende or f"Vidéo #{self.pk}"

    class Meta:
        verbose_name = "Vidéo de la salle"
        verbose_name_plural = "Vidéos de la salle"
        ordering = ["ordre_affichage", "-date_ajout"]


class PhotoSalle(models.Model):
    """
    Galerie "ambiance de la salle", affichée sur l'accueil. Purement
    éditoriale (aucune logique métier) — l'objectif est de rendre le site
    vivant avec de vraies photos de T-GYM plutôt que des stocks génériques.
    Section masquée automatiquement sur le site tant qu'aucune photo n'est
    en ligne (pas de placeholder cassé avant que le staff n'en ajoute).
    """
    image = models.ImageField("Photo", upload_to="galerie/")
    legende = models.CharField("Légende (optionnelle)", max_length=150, blank=True)
    actif = models.BooleanField("Visible sur le site", default=True)
    ordre_affichage = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_ajout = models.DateTimeField("Ajoutée le", default=timezone.now)

    def __str__(self):
        return self.legende or f"Photo #{self.pk}"

    class Meta:
        verbose_name = "Photo de la salle (galerie)"
        verbose_name_plural = "Photos de la salle (galerie)"
        ordering = ["ordre_affichage", "-date_ajout"]


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
