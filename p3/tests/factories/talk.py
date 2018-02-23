import factory

from conference.tests.factories.talk import TalkFactory


class P3TalkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'p3.P3Talk'

    talk = factory.SubFactory(TalkFactory)
