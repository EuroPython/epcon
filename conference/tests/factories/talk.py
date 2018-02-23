from __future__ import absolute_import

import factory
import factory.django
import factory.fuzzy
from django.template.defaultfilters import slugify
from faker import Faker

import conference.models
from conference.models import TALK_LANGUAGES
from conference.tests.factories.speaker import SpeakerFactory

fake = Faker()

class TalkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Talk'

    title = factory.LazyAttribute(lambda talk: fake.sentence(nb_words=6, variable_nb_words=True)[:80])
    sub_title = factory.Faker('sentence', nb_words=12, variable_nb_words=True)

    duration = 30

    slug = factory.LazyAttribute(lambda talk: slugify(talk.title))
    level = factory.Iterator(conference.models.TALK_LEVEL, getter=lambda x: x[0])
    status = factory.Iterator(conference.models.TALK_STATUS, getter=lambda x: x[0])
    conference = factory.Iterator(conference.models.Conference.objects.all().values_list('code', flat=True))
    language = factory.Iterator(TALK_LANGUAGES, getter=lambda x: x[0])

class TalkSpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.TalkSpeaker'

    talk = factory.SubFactory(TalkFactory)
    speaker = factory.SubFactory(SpeakerFactory)
