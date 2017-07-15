import factory

from p3.tests.factories.schedule import ScheduleFactory


class TrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Track'

    schedule = factory.SubFactory(ScheduleFactory)

    track = factory.Sequence(lambda x: 'track%05d' % x)
    seats = 100