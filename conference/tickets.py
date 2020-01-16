from django.db.models import Q

from p3.models import TicketConference
from conference.models import Ticket
from conference.fares import FARE_CODE_REGEXES, FARE_CODE_VARIANTS

def reset_ticket_settings(ticket):
    tc = ticket.p3_conference
    new_tc = TicketConference()  # won't save this, created just to copy defaults from it
    tc.shirt_size = new_tc.shirt_size
    tc.diet = new_tc.diet
    tc.tagline = new_tc.tagline
    tc.days = new_tc.days
    tc.save()
    return tc


def sold_training_tickets_including_combined_tickets(conference_code):
    qs = Ticket.objects.filter(
        fare__conference=conference_code,
        frozen=False,
        orderitem__order___complete=True,
    ).filter(
        Q(
            fare__code__regex=FARE_CODE_REGEXES["variants"][
                FARE_CODE_VARIANTS.TRAINING
            ]
        )
        | Q(
            fare__code__regex=FARE_CODE_REGEXES["variants"][
                FARE_CODE_VARIANTS.COMBINED
            ]
        )
    )
    return qs
