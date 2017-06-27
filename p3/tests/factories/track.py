import factory

from p3.tests.factories.schedule import ScheduleFactory


class TrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Track'

    schedule = factory.SubFactory(ScheduleFactory)

    track = factory.Sequence(lambda x: 'Track %05d' % x)
    seats = 100