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

    return {
        "site_config": SiteConfig.get_solo(),
        "annonce_active": annonce_active,
        "programme_phare": programme_phare,
        "actualite_phare": actualite_phare,
    }



