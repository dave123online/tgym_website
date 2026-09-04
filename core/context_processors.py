from django.conf import settings
from django.core.cache import cache

from actualites.models import Actualite
from coaching.models import Programme
from core.models import Annonce, SiteConfig

# Clé de cache + durée de vie du contexte global (config du site, annonce
# active, programme phare, actu phare). Ces données sont identiques pour
# TOUT visiteur (pas de personnalisation par utilisateur) et ne changent
# que quand le staff les modifie dans l'admin — inutile de retaper la
# base à chaque chargement de page. Avant ce cache, chaque requête (y
# compris les dizaines de bots/scanners qui tapent le site en continu)
# déclenchait 3-4 requêtes SQL rien que pour ce contexte, ce qui gonflait
# la conso de compute hours Neon sans aucun bénéfice utilisateur.
CLE_CACHE_CONTEXTE_GLOBAL = "core:contexte_global_site"
DUREE_CACHE_SECONDES = 60*60*24  # 24 heures — filet de sécurité ; core.signals vide
                             # le cache immédiatement dès qu'un admin modifie
                             # une de ces données, donc pas besoin d'attendre.


def _charger_contexte_global() -> dict:
    """Va réellement chercher les données en base — appelé uniquement en
    cas de cache manquant/expiré, jamais directement à chaque requête."""
    annonce_active = (
        Annonce.objects.filter(actif=True).order_by("-date_debut").first()
    )
    if annonce_active and not annonce_active.est_visible():
        annonce_active = None

    programme_phare = Programme.objects.filter(actif=True, est_phare=True).first()

    actualite_phare = (
        Actualite.objects.filter(est_publiee=True, is_featured=True)
        .order_by("-date_publication")
        .first()
    )

    return {
        "site_config": SiteConfig.get_solo(),
        "annonce_active": annonce_active,
        "programme_phare": programme_phare,
        "actualite_phare": actualite_phare,
    }


def site_config(request):
    """
    Injecte la config du site, l'annonce active, le programme phare et
    l'actualité mise en avant dans le contexte de CHAQUE template, comme
    'active_theme' le fait sur akem_fs. Cette partie est mise en cache
    (cf. CLE_CACHE_CONTEXTE_GLOBAL) car identique pour tous les visiteurs.
    """
    contexte = cache.get(CLE_CACHE_CONTEXTE_GLOBAL)
    if contexte is None:
        contexte = _charger_contexte_global()
        cache.set(CLE_CACHE_CONTEXTE_GLOBAL, contexte, DUREE_CACHE_SECONDES)

    # canonical_url dépend de l'URL de LA requête en cours : jamais mis
    # en cache avec le reste, sinon toutes les pages afficheraient la
    # même URL canonique (celle de la première page qui a rempli le cache).
    canonical_url = f"{settings.SITE_URL.rstrip('/')}{request.path}"

    return {**contexte, "canonical_url": canonical_url}
