from django.conf import settings

from actualites.models import Actualite
from coaching.models import Programme
from core.models import Annonce, SiteConfig


def site_config(request):
    """
    Injecte la config du site, l'annonce active, le programme phare et
    l'actualité mise en avant dans le contexte de CHAQUE template, comme
    'active_theme' le fait sur akem_fs.
    """
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

    # URL canonique forcée sur le domaine principal (SITE_URL), quel que
    # soit le domaine réellement utilisé pour accéder à la page. Utile
    # même une fois les redirections 301 .htaccess de .online/.site en
    # place : ça élimine aussi les variantes www/non-www et les query
    # strings de tracking (?utm_...) qui, sans canonical, seraient vues
    # par Google comme des pages dupliquées de la même page.
    canonical_url = f"{settings.SITE_URL.rstrip('/')}{request.path}"

    return {
        "site_config": SiteConfig.get_solo(),
        "annonce_active": annonce_active,
        "programme_phare": programme_phare,
        "actualite_phare": actualite_phare,
        "canonical_url": canonical_url,
    }

