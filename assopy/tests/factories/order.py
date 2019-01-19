import factory

from assopy.tests.factories.user import AssopyUserFactory


class CreditCardOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.Order'

    user = factory.SubFactory(AssopyUserFactory)

    payment = 'cc' # cc because stripe is a credit card
    items = []
