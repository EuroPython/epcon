import factory
import factory.django

from django_factory_boy import auth as auth_factories


class SpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Speaker'

    user = factory.SubFactory(auth_factories.UserFactory)