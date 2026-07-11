from django.apps import AppConfig


class ComptesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'comptes'
    verbose_name = "Comptes & rôles"

    def ready(self):
        import comptes.signals  # noqa



