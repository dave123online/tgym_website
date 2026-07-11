from django.shortcuts import get_object_or_404, render

from .models import Actualite


def actualites(request):
    liste = Actualite.objects.filter(est_publiee=True)
    return render(request, "actualites/actualites.html", {"actualites": liste})


def actualite_detail(request, slug):
    actualite = get_object_or_404(Actualite, slug=slug, est_publiee=True)
    return render(request, "actualites/actualite_detail.html", {"actualite": actualite})



