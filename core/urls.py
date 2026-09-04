from django.urls import path

from . import views

app_name = "core"
from django.views.generic import TemplateView


urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("methode/", views.methode, name="methode"),
    path("tarifs/", views.tarifs, name="tarifs"),
    path("ou-nous-trouver/", views.ou_nous_trouver, name="ou_nous_trouver"),
    path("chatbot/message/", views.chatbot_message, name="chatbot_message"),
    path("politique-confidentialite/", views.politique_confidentialite, name="politique_confidentialite"),
    path("sitemap.xml", TemplateView.as_view(template_name="core/sitemap.xml", content_type="application/xml"), name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="core/robots.txt", content_type="text/plain"), name="robots"),
]
