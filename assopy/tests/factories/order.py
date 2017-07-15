import factory

from .user import UserFactory


class CreditCardOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assopy.Order'

    user = factory.SubFactory(UserFactory)

    payment = 'cc' # cc because stripe is a credit card
    items = []
