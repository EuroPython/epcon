from p3.models import TicketConference


def assign_ticket_to_user(ticket, user):
    ticket.user = user
    ticket.save()
    try:
        ticket.p3_conference
    except TicketConference.DoesNotExist:
        TicketConference.objects.create(ticket=ticket)
        ticket.refresh_from_db()

    ticket.p3_conference.assigned_to = user.email
    ticket.p3_conference.save()
    return ticket


# TODO: Move this somewhere else. Settings maybe(?)
DEFAULT_SHIRT_SIZE = 'l'
DEFAULT_DIET = 'omnivorous'


def reset_ticket_settings(ticket):
    tc = ticket.p3_conference
    tc.shirt_size = DEFAULT_SHIRT_SIZE
    tc.diet = DEFAULT_DIET
    tc.tagline = ''
    tc.days = ''
    tc.save()
    return tc
