from django.apps import AppConfig


class ConferenceConfig(AppConfig):
    name = 'conference'

    def ready(self):
        import conference.listeners  # noqa
