from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "core"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("methode/", views.methode, name="methode"),
    path("tarifs/", views.tarifs, name="tarifs"),
    path("ou-nous-trouver/", views.ou_nous_trouver, name="ou_nous_trouver"),
    path("chatbot/message/", views.chatbot_message, name="chatbot_message"),
    path("politique-confidentialite/", views.politique_confidentialite, name="politique_confidentialite"),
    # Sitemap généré dynamiquement (voir views.sitemap_xml) : inclut désormais
    # chaque programme actif et chaque actualité publiée, avec lastmod.
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="core/robots.txt", content_type="text/plain"), name="robots"),
]
