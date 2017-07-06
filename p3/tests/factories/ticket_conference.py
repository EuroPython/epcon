import factory

from conference.models import Ticket
from p3.models import TICKET_CONFERENCE_SHIRT_SIZES, TICKET_CONFERENCE_DIETS


class TicketConferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'p3.TicketConference'

    ticket = factory.SubFactory(Ticket)
    diet = factory.Iterator(TICKET_CONFERENCE_DIETS, getter=lambda x:x[0])
    shirt_size = factory.Iterator(TICKET_CONFERENCE_SHIRT_SIZES, getter=lambda x: x[0])