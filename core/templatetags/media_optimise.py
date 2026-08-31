"""
Filtres pour optimiser automatiquement les médias servis via Cloudinary,
sans rien changer côté upload/modèles — on transforme juste l'URL au
moment de l'affichage.

Avant ce fix, les <img>/<video> du site pointaient directement vers les
fichiers originaux uploadés (souvent plusieurs Mo pour une photo prise au
téléphone) — display .url sans aucune transformation. Sur une connexion
lente (2G/3G, cas courant en Afrique de l'Ouest hors grandes villes),
cela peut suffire à empêcher la page de charger.

f_auto : Cloudinary sert automatiquement le format le plus léger que le
         navigateur du visiteur supporte (WebP/AVIF plutôt que JPEG/PNG).
q_auto : Cloudinary choisit automatiquement le niveau de compression le
         moins perceptible visuellement pour le poids le plus faible.
w_auto / une largeur max raisonnable : évite de servir une image 4000px
         de large pour un affichage qui n'en fait jamais plus de ~1200.
"""
from django import template

register = template.Library()

_TRANSFORMATIONS_PAR_DEFAUT = "f_auto,q_auto"


def _inserer_transformation(url: str, transformation: str) -> str:
    """Insère la chaîne de transformation Cloudinary juste après
    `/upload/` dans l'URL. Si l'URL ne vient pas de Cloudinary (ex: dev
    local en FileSystemStorage, ou URL vide), on la retourne inchangée —
    ce filtre ne doit jamais casser l'affichage, au pire il est un no-op."""
    if not url or "/upload/" not in url:
        return url
    avant, apres = url.split("/upload/", 1)
    return f"{avant}/upload/{transformation}/{apres}"


@register.filter(name="cloud_img")
def cloud_img(url, largeur_max: int = 1200):
    """Optimise une image : format + qualité auto, largeur plafonnée
    (l'image n'est jamais réduite plus que sa taille d'origine, seulement
    limitée vers le haut)."""
    if not url:
        return url
    return _inserer_transformation(str(url), f"{_TRANSFORMATIONS_PAR_DEFAUT},w_{largeur_max},c_limit")


@register.filter(name="cloud_video")
def cloud_video(url, largeur_max: int = 960):
    """Optimise une vidéo : format + qualité auto (Cloudinary transcode à
    la volée en WebM/H.265 selon le navigateur si plus léger), largeur
    plafonnée — une vidéo de fond n'a jamais besoin d'être en 4K."""
    if not url:
        return url
    return _inserer_transformation(str(url), f"{_TRANSFORMATIONS_PAR_DEFAUT},w_{largeur_max},c_limit")
