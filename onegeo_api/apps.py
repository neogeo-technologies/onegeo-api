from django.apps import AppConfig


class OnegeoAPIConfig(AppConfig):
    name = 'onegeo_api'

    def ready(self):
        import onegeo_api.signals
