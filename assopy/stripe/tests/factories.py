from __future__ import absolute_import
from __future__ import unicode_literals

from django.utils import timezone

import factory
from factory import fuzzy


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'auth.User'

    username = fuzzy.FuzzyText()
    password = factory.PostGenerationMethodCall("set_password", "123456")
    is_active = True
    email = fuzzy.FuzzyText(suffix="@bar.it")


class AssopyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.User'

    user = factory.SubFactory(UserFactory)


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Order"

    user = factory.SubFactory(AssopyUserFactory)
    payment = "cc"


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.OrderItem"


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"


class VatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Vat"

    value = 21


class VatFareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.VatFare"

    vat = factory.SubFactory(VatFactory)
    fare = None


class FareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Fare"

    vats = factory.RelatedFactory(VatFareFactory, "fare")
    conference = "testconf"
    code = "TOSP"
    name = fuzzy.FuzzyText()
    price = 10

    @factory.lazy_attribute
    def start_validity(self):
        return timezone.now() - timezone.timedelta(days=10)

    @factory.lazy_attribute
    def end_validity(self):
        return timezone.now() + timezone.timedelta(days=10)
