from django.apps import AppConfig


class AbonnementsConfig(AppConfig):
    name = 'abonnements'

    def ready(self):
        import abonnements.signals  # noqa
