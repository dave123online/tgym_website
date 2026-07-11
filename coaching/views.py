from django.shortcuts import get_object_or_404, render

from core.whatsapp import build_generic_whatsapp_link

from .models import Programme


def programmes(request):
    liste = Programme.objects.filter(actif=True)
    return render(request, "coaching/programmes.html", {"programmes": liste})


def programme_detail(request, slug):
    programme = get_object_or_404(Programme, slug=slug, actif=True)
    sujet = f"le programme {programme.titre}"
    contact_link = build_generic_whatsapp_link(sujet)
    return render(request, "coaching/programme_detail.html", {
        "programme": programme,
        "contact_link": contact_link,
    })



