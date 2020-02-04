from django.apps import AppConfig


class P3Config(AppConfig):
    name = 'p3'

    def ready(self):
        import p3.listeners  # noqa
