import datetime

import factory
import factory.django

from conference.tests.factories.conference import ConferenceFactory


class HotelBookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'p3.HotelBooking'

    conference = factory.SubFactory(ConferenceFactory)

    booking_start = factory.Faker('date_time_this_decade', before_now=True, after_now=True)
    booking_end = factory.LazyAttribute(lambda conf: (conf.booking_start + datetime.timedelta(days=+5)))

    default_start = factory.LazyAttribute(lambda conf: conf.booking_start)
    default_end = factory.LazyAttribute(lambda conf: conf.booking_end)