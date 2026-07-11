from django.urls import path

from . import views

app_name = "comptes"

urlpatterns = [
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views.DeconnexionView.as_view(), name="deconnexion"),
    path("mon-espace/", views.mon_espace, name="mon_espace"),
    path("creer-compte/", views.creer_compte_adherent, name="creer_compte_adherent"),
    path("mot-de-passe/", views.ChangerMotDePasseView.as_view(), name="changer_mot_de_passe"),
    path("mot-de-passe/termine/", views.ChangerMotDePasseTermineView.as_view(), name="changer_mot_de_passe_termine"),
]



