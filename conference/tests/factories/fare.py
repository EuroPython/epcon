from __future__ import absolute_import

import functools

import factory
import factory.django
from decimal import Decimal
from django.template.defaultfilters import slugify
from django_factory_boy import auth as auth_factories

import conference.models
from conference.models import (FARE_TYPES,
                               FARE_TICKET_TYPES,
                               FARE_PAYMENT_TYPE,
                               TICKET_TYPE,
                               )

from random import randint

Iterator = functools.partial(factory.Iterator, getter=lambda x: x[0])


class FareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Fare'

    conference = factory.Iterator(conference.models.Conference.objects.all().values_list('code', flat=True))
    code = factory.Sequence(lambda n: 'Code%04d' % n)
    name = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    recipient_type = Iterator(FARE_TYPES)
    ticket_type = Iterator(FARE_TICKET_TYPES)
    payment_type = Iterator(FARE_PAYMENT_TYPE)
    price = factory.LazyAttribute(lambda f: Decimal(randint(1, 200)))


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Ticket'

    user = factory.SubFactory(auth_factories.UserFactory)
    name = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    fare = factory.SubFactory(FareFactory)
    frozen = factory.Faker('random_element', elements=(True, False))
    ticket_type = Iterator(TICKET_TYPE)


class SponsorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Sponsor'

    sponsor = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    slug = factory.LazyAttribute(lambda sponsor: slugify(sponsor.sponsor))
    url = factory.Faker('url')