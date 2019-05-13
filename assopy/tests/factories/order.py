from datetime import timedelta
import uuid

import factory

from django.utils import timezone

from assopy.tests.factories.user import AssopyUserFactory
import conference.models


class CreditCardOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.Order'

    user = factory.SubFactory(AssopyUserFactory)

    payment = 'cc' # cc because stripe is a credit card
    items = []


class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.Coupon'

    conference = factory.Iterator(conference.models.Conference.objects.all())
    value = '10%'
    code = factory.LazyAttribute(lambda _: uuid.uuid4().hex)
    start_validity = factory.LazyAttribute(lambda _: timezone.now().date())
    end_validity = factory.LazyAttribute(lambda _: timezone.now().date() + timedelta(days=1))

    @factory.post_generation
    def fares(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for fare in extracted:
                self.fares.add(fare)
        else:
            self.fares.add(*conference.models.Fare.objects.all())
