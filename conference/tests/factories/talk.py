

import factory
import factory.django
import factory.fuzzy
from django.conf import settings
from django.template.defaultfilters import slugify

import conference.models
from conference.models import TALK_LANGUAGES
from conference.tests.factories.speaker import SpeakerFactory


class TalkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Talk'

    title = factory.LazyAttribute(
        lambda talk: factory.Faker(
            'sentence', nb_words=6, variable_nb_words=True
        ).generate({})[:80]
    )
    sub_title = factory.Faker('sentence', nb_words=12, variable_nb_words=True)

    duration = 30

    slug = factory.LazyAttribute(lambda talk: slugify(talk.title))
    level = factory.Iterator(
        conference.models.TALK_LEVEL, getter=lambda x: x[0]
    )
    status = factory.Iterator(
        conference.models.TALK_STATUS, getter=lambda x: x[0]
    )
    conference = factory.Iterator(
        conference.models.Conference.objects.all().values_list(
            'code', flat=True
        )
    )
    language = factory.Iterator(TALK_LANGUAGES, getter=lambda x: x[0])


class TalkSpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.TalkSpeaker'

    talk = factory.SubFactory(TalkFactory)
    speaker = factory.SubFactory(SpeakerFactory)


class CommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = 'django_comments.Comment'

    comment = factory.Faker('sentence', nb_words=12, variable_nb_words=True)
    site_id = settings.SITE_ID
    content_object = factory.SubFactory(TalkFactory)
