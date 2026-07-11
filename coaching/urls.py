from django.urls import path

from . import views

app_name = "coaching"

urlpatterns = [
    path("programmes/", views.programmes, name="programmes"),
    path("programmes/<slug:slug>/", views.programme_detail, name="programme_detail"),
]



