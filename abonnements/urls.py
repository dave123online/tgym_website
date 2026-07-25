from django.urls import path

from . import views, views_cron, views_diffusion, views_reponse

app_name = "abonnements"

urlpatterns = [
    path("webhook/whatsapp/", views.whatsapp_webhook, name="webhook_whatsapp"),
    path("admin-diffusion/whatsapp/", views_diffusion.diffusion_whatsapp, name="diffusion_whatsapp"),
    path("admin-conversation/<int:pk>/repondre/", views_reponse.repondre_conversation, name="repondre_conversation"),
    path("cron/relances/", views_cron.declencher_relances, name="cron_relances"),
]
