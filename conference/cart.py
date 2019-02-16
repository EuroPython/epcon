
from datetime import datetime

from django.conf.urls import url
from django.template.response import TemplateResponse

from .fares import (
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
    get_available_fares,
)


def cart_step1_choose_type_of_order(request):
    """
    This view is not login required because we want to display some summary of
    ticket prices here as well.
    """

    return TemplateResponse(
        request, "ep19/cart/step_1_choose_type_of_order.html", {},
    )


class TicketType:
    personal = 'personal'
    company = 'company'
    student = 'student'

    ALL = [personal, company, student]


# TODO: move to fares
def get_available_fares_for_type(type_of_tickets):
    assert type_of_tickets in TicketType.ALL

    fares = get_available_fares(datetime.now().date())

    if type_of_tickets == TicketType.personal:
        regex_group = FARE_CODE_GROUPS.PERSONAL
    if type_of_tickets == TicketType.company:
        regex_group = FARE_CODE_GROUPS.COMPANY
    if type_of_tickets == TicketType.student:
        regex_group = FARE_CODE_GROUPS.STUDENT

    fares = fares.filter(
        code__regex=FARE_CODE_REGEXES["groups"][regex_group]
    )

    return fares


def cart_step2_pick_tickets(request, type_of_tickets):
    """
    Only submit this form if user is authenticated, otherwise dispaly some
    support info.
    """

    if type_of_tickets in TicketType.ALL:
        available_fares = get_available_fares_for_type(type_of_tickets)
    else:
        raise NotImplementedError("Type not a fare", type_of_tickets)

    return TemplateResponse(
        request, "ep19/cart/step_2_pick_tickets.html", {
            'type_of_tickets': type_of_tickets,
            'available_fares': available_fares,
        },
    )


urlpatterns_ep19 = [
    url(r'^$', cart_step1_choose_type_of_order, name="step1_choose_type"),
    url(r'^(?P<type_of_tickets>\w+)/$',
        cart_step2_pick_tickets,
        name="step2_pick_tickets"),
]
