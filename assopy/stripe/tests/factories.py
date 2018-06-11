# coding: utf-8

from __future__ import absolute_import, unicode_literals

import random

from django.utils import timezone

import factory
from factory import fuzzy

from conference.fares import AVAILABLE_FARE_CODES


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
    address = "Random Street 42\n31-337 SomeCity\nRandomCountry"


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.OrderItem"


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"


class VatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Vat"

    value = 20


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
    price = 10

    @factory.lazy_attribute
    def code(self):
        return random.choice(AVAILABLE_FARE_CODES.keys())

    @factory.lazy_attribute
    def name(self):
        return "EuroPython2018 – %s" % AVAILABLE_FARE_CODES[self.code]

    @factory.lazy_attribute
    def start_validity(self):
        return timezone.now() - timezone.timedelta(days=10)

    @factory.lazy_attribute
    def end_validity(self):
        return timezone.now() + timezone.timedelta(days=10)
