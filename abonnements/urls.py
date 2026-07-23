from django.urls import path

from . import views

app_name = "abonnements"

urlpatterns = [
    path("webhook/whatsapp/", views.whatsapp_webhook, name="webhook_whatsapp"),
]
