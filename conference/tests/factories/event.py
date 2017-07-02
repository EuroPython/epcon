import factory
import factory.django

from .talk import TalkFactory
from p3.tests.factories.schedule import ScheduleFactory
from p3.tests.factories.track import TrackFactory


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Event'

    schedule = factory.SubFactory(ScheduleFactory)
    talk = factory.SubFactory(TalkFactory)


class EventTrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.EventTrack'

    track = factory.SubFactory(TrackFactory)
    event = factory.SubFactory(EventFactory)


class TrackWithEventsFactory(TrackFactory):
    event1 = factory.RelatedFactory(EventTrackFactory, 'event')
    event2 = factory.RelatedFactory(EventTrackFactory, 'event')
