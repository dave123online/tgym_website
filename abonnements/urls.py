from django.urls import path

from . import views, views_cron, views_diffusion, views_reponse, views_staff

app_name = "abonnements"

urlpatterns = [
    path("webhook/whatsapp/", views.whatsapp_webhook, name="webhook_whatsapp"),
    path("admin-diffusion/whatsapp/", views_diffusion.diffusion_whatsapp, name="diffusion_whatsapp"),
    path("admin-conversation/<int:pk>/repondre/", views_reponse.repondre_conversation, name="repondre_conversation"),
    path("cron/relances/", views_cron.declencher_relances, name="cron_relances"),
    path("staff/conversations/", views_staff.liste_conversations, name="staff_conversations"),
    path("staff/conversations/<int:pk>/", views_staff.detail_conversation, name="staff_conversation_detail"),
    path("staff/conversations/<int:pk>/mode/", views_staff.changer_mode_conversation, name="staff_conversation_mode"),
]

