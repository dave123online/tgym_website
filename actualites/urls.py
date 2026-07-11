from django.urls import path

from . import views

app_name = "actualites"

urlpatterns = [
    path("actualites/", views.actualites, name="actualites"),
    path("actualites/<slug:slug>/", views.actualite_detail, name="actualite_detail"),
]



