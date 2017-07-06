import factory

from conference.models import Ticket
from p3.models import TICKET_CONFERENCE_SHIRT_SIZES

class TicketConferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'p3.TicketConference'

    ticket = factory.SubFactory(Ticket)
    shirt_size = factory.Iterator(TICKET_CONFERENCE_SHIRT_SIZES, getter=lambda x: x[0])