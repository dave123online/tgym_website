from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from actualites.models import Actualite
from coaching.models import Programme
from core.context_processors import CLE_CACHE_CONTEXTE_GLOBAL
from core.models import Annonce, SiteConfig


def _vider_cache_contexte_global(**kwargs):
    """
    Invalide immédiatement le cache du contexte global (cf.
    core.context_processors.site_config) dès qu'un admin modifie une
    des données concernées — SiteConfig, Annonce, Programme ou
    Actualite. Sans ça, une modification faite dans l'admin Django
    mettrait jusqu'à 5 minutes (DUREE_CACHE_SECONDES) à apparaître sur
    le site, ce qui serait déroutant pour le staff en train de tester
    un changement.
    """
    cache.delete(CLE_CACHE_CONTEXTE_GLOBAL)


# post_save ET post_delete : une annonce/programme/actu supprimée doit
# aussi disparaître immédiatement du site, pas seulement une modif.
for _modele in (SiteConfig, Annonce, Programme, Actualite):
    post_save.connect(_vider_cache_contexte_global, sender=_modele, weak=False)
    post_delete.connect(_vider_cache_contexte_global, sender=_modele, weak=False)
