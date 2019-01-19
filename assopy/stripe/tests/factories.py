



import random

from django.utils import timezone

import factory
from factory import fuzzy
from faker import Faker

from conference.fares import AVAILABLE_FARE_CODES


fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth.User'

    username = fuzzy.FuzzyText()
    password = factory.PostGenerationMethodCall("set_password", "123456")
    is_active = True
    email = fuzzy.FuzzyText(suffix="@bar.it")
    assopy_user = factory.RelatedFactory('assopy.stripe.tests.factories.AssopyUserFactory', 'user')


class AssopyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.AssopyUser'

    user = factory.SubFactory(UserFactory, assopy_user=factory.LazyAttribute(lambda assopy_user: assopy_user))


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.Country'

    iso = factory.Faker('country_code')
    name = factory.Faker('country')


class VatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Vat"

    value = 20


class FareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Fare"

    vats = factory.RelatedFactory('assopy.stripe.tests.factories.VatFareFactory', 'fare')
    conference = "testconf"
    price = 10

    @factory.lazy_attribute
    def code(self):
        return random.choice(list(AVAILABLE_FARE_CODES.keys()))

    @factory.lazy_attribute
    def name(self):
        return "EuroPython2019 – %s" % AVAILABLE_FARE_CODES[self.code]

    @factory.lazy_attribute
    def start_validity(self):
        return timezone.now() - timezone.timedelta(days=10)

    @factory.lazy_attribute
    def end_validity(self):
        return timezone.now() + timezone.timedelta(days=10)


class VatFareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.VatFare"

    vat = factory.SubFactory(VatFactory)
    fare = factory.SubFactory(FareFactory, vats=factory.LazyAttribute(lambda vat_fare: vat_fare))


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"

    user = factory.SubFactory(UserFactory)
    fare = factory.SubFactory(FareFactory)


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.OrderItem"

    ticket = factory.SubFactory(TicketFactory)
    vat = factory.SubFactory(VatFactory)
    # NOTE umgelurgel (2018-10-20)
    # As this depends on `OrderFactory` to work independently, this factory is not independent either.
    order = factory.SubFactory('assopy.stripe.tests.factories.OrderFactory')


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Order"

    user = factory.SubFactory(AssopyUserFactory)
    payment = "cc"
    _complete = False
    # NOTE umgelurgel (2018-10-20)
    # `items` needs to be passed to the Order.objects.create(), which is a list of (FareFactory, dict)
    # The spaghetti of signal dependencies makes it challenging to identify where or why
    # does that fail to work correctly.
    # This also requires to mock out email sending in tests that use it.
    # items = factory.LazyAttribute(lambda order: [(FareFactory(), {"qty": 1})])

    country = factory.SubFactory(CountryFactory)

    @factory.lazy_attribute
    def address(self):
        return '\n'.join([fake.address(), self.country.name])
