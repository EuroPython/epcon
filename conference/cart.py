
from datetime import datetime

from django.conf.urls import url
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.utils import timezone

from .orders import (
    create_order,
    calculate_order_price_including_discount,
    OrderCalculation,
)
from .fares import (
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
    get_available_fares,
)


GLOBAL_MAX_PER_FARE_TYPE = 6


def cart_step1_choose_type_of_order(request):
    """
    This view is not login required because we want to display some summary of
    ticket prices here as well.
    """

    return TemplateResponse(
        request, "ep19/cart/step_1_choose_type_of_order.html", {},
    )


def cart_step2_pick_tickets(request, type_of_tickets):
    """
    Only submit this form if user is authenticated, otherwise dispaly some
    support info.
    """

    assert type_of_tickets in TicketType.ALL

    available_fares = get_available_fares_for_type(type_of_tickets)
    context = {
        "CartActions": CartActions,
        "available_fares": available_fares,
        "global_max_per_fare_type": GLOBAL_MAX_PER_FARE_TYPE,
        'calculation': OrderCalculation(0, 0, 0),  # empty calculation
        'currency': "EUR",
        'fares_info': {},  # empty fares info
    }

    if request.method == 'POST':

        discount_code, fares_info = extract_order_parameters_from_request(
            request.POST
        )
        context['fares_info'] = fares_info

        calculation, coupon = calculate_order_price_including_discount(
            for_user=request.user,
            for_date=timezone.now().date(),
            fares_info=fares_info,
            discount_code=discount_code,
        )

        if CartActions.apply_discount_code in request.POST:
            context['calculation'] = calculation
            context['discount_code'] = discount_code or 'No discount code'

        if CartActions.buy_tickets in request.POST:
            order = create_order(
                for_user=request.user,
                for_date=timezone.now().date(),
                fares_info=fares_info,
                calculation=calculation,
                coupon=coupon,
            )
            return redirect(
                "cart:step3_add_billing_info",
                order_id=order.id,
            )

    return TemplateResponse(
        request, "ep19/cart/step_2_pick_tickets.html", context
    )


def cart_step3_add_billing_info(request, order_id):

    return TemplateResponse(
        request, "ep19/cart/step_3_add_billing_info.html", {}
    )


def extract_order_parameters_from_request(post_data):

    discount_code = None
    fares_info = {}

    for k, v in post_data.items():
        if k == 'discount_code':
            discount_code = v

        elif is_available_fare(k):
            try:
                fares_info[k] = int(v)
            except ValueError:
                pass

    return discount_code, fares_info


def is_available_fare(fare_code):
    return True


class TicketType:
    personal = 'personal'
    company = 'company'
    student = 'student'

    ALL = [personal, company, student]


class CartActions:
    apply_discount_code = 'apply_discount_code'
    buy_tickets = 'buy_tickets'


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


urlpatterns_ep19 = [
    url(r'^$', cart_step1_choose_type_of_order, name="step1_choose_type"),
    url(r'^(?P<type_of_tickets>\w+)/$',
        cart_step2_pick_tickets,
        name="step2_pick_tickets"),

    # TODO: replace with uuid
    url(r'^add-billing/(?P<order_id>\d+)/$',
        cart_step3_add_billing_info,
        name="step3_add_billing_info"),
]
