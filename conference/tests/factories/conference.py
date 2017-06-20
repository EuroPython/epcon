import datetime

import factory
import factory.fuzzy
import factory.django


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

    code = factory.Sequence(lambda x: 'CONF%05d' % x)
    name = factory.Faker('sentence', nb_words=6, variable_nb_words=True)

    cfp_start = factory.LazyAttribute(lambda conf: conf.conference_start - datetime.timedelta(days=50))
    cfp_end = factory.LazyAttribute(lambda conf: conf.cfp_start + datetime.timedelta(days=+20))

    conference_start = factory.Faker('date_time_this_decade', before_now=True, after_now=True)
    conference_end = factory.LazyAttribute(lambda conf: (conf.conference_start + datetime.timedelta(days=+5)))

    voting_start = factory.LazyAttribute(lambda conf: conf.cfp_end + datetime.timedelta(days=10))
    voting_end = factory.LazyAttribute(lambda conf: conf.voting_start + datetime.timedelta(days=5))