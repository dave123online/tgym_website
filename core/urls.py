from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("methode/", views.methode, name="methode"),
    path("tarifs/", views.tarifs, name="tarifs"),
    path("ou-nous-trouver/", views.ou_nous_trouver, name="ou_nous_trouver"),
    path("chatbot/message/", views.chatbot_message, name="chatbot_message"),
]



