import datetime

import factory
import factory.django
import factory.fuzzy
from faker import Faker

from django.conf import settings

fake = Faker()


class ConferenceTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.ConferenceTag'

    category = factory.Faker('word')


class ConferenceTaggedItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.ConferenceTaggedItem'

    tag = factory.SubFactory(ConferenceTagFactory)


class ConferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Conference'

    code = settings.CONFERENCE_CONFERENCE
    name = factory.Faker('sentence', nb_words=6, variable_nb_words=True)

    cfp_start = factory.LazyAttribute(lambda conf: conf.conference_start - datetime.timedelta(days=50))
    cfp_end = factory.LazyAttribute(lambda conf: conf.cfp_start + datetime.timedelta(days=+20))

    @factory.lazy_attribute
    def conference_start(self):
        return fake.date_time_this_decade(before_now=True, after_now=True).date()
    # conference_start = factory.Faker('date_time_this_decade', before_now=True, after_now=True)
    conference_end = factory.LazyAttribute(lambda conf: (conf.conference_start + datetime.timedelta(days=+5)))

    voting_start = factory.LazyAttribute(lambda conf: conf.cfp_end + datetime.timedelta(days=10))
    voting_end = factory.LazyAttribute(lambda conf: conf.voting_start + datetime.timedelta(days=5))