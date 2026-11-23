from django.apps import AppConfig


class AutosConfig(AppConfig):
    name = "autos"
    
    def ready(self):
        from . import signals  # noqa