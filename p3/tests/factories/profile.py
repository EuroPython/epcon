import factory

from conference.tests.factories.attendee_profile import AttendeeProfileFactory


class P3ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'p3.P3Profile'

    profile = factory.RelatedFactory(AttendeeProfileFactory)