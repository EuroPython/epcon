import uuid
from datetime import datetime, date

from django.conf.urls import url
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponse
from django import forms

from conference.models import StripePayment

from .invoicing import create_invoices_for_order

from .orders import (
    create_order,
    calculate_order_price_including_discount,
    is_business_order,
    Order,
    OrderCalculation,
)
from .fares import (
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
    get_available_fares,
    FareIsNotAvailable,
)

from .payments import charge_for_payment, PaymentError


GLOBAL_MAX_PER_FARE_TYPE = 6


def cart_step1_choose_type_of_order(request):
    """
    This view is not login required because we want to display some summary of
    ticket prices here as well.
    """

    return TemplateResponse(
        request, "ep19/bs/cart/step_1_choose_type_of_order.html", {}
    )


@login_required
@staff_member_required  # TEMPORARY for testing
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

        try:
            calculation, coupon = calculate_order_price_including_discount(
                for_user=request.user,
                for_date=timezone.now().date(),
                fares_info=fares_info,
                discount_code=discount_code,
            )
        except FareIsNotAvailable:
            return HttpResponse("Fare is not available", status=403)

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
                "cart:step3_add_billing_info", order_uuid=order.uuid
            )

    return TemplateResponse(
        request, "ep19/bs/cart/step_2_pick_tickets.html", context
    )


@login_required
@staff_member_required  # TEMPORARY for testing
def cart_step3_add_billing_info(request, order_uuid):

    order = get_object_or_404(Order, uuid=order_uuid)

    if is_business_order(order):
        billing_form = BusinessBillingForm
    else:
        # TODO: should we have a student billing form?
        billing_form = PersonalBillingForm

    form = billing_form(instance=order)

    if request.method == 'POST':
        form = billing_form(data=request.POST, instance=order)

        if form.is_valid():
            form.save()
            # TODO(artcz)
            # if form billing notes then create custom helpdesk case?

            return redirect("cart:step4_payment", order_uuid=order.uuid)

    return TemplateResponse(
        request, "ep19/bs/cart/step_3_add_billing_info.html", {'form': form}
    )


@login_required
@staff_member_required  # TEMPORARY for testing
def cart_step4_payment(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)
    total_for_stripe = int(order.total() * 100)
    payments = order.stripepayment_set.all().order_by('created')
    # TODO: pay attention if order is paid or not, and if paid don't render the
    # payment button in the template

    if request.method == 'POST':
        stripe_payment = StripePayment.objects.create(
            order=order,
            user=request.user,
            uuid=str(uuid.uuid4()),
            amount=order.total(),
            token=request.POST.get('stripeToken'),
            token_type=request.POST.get('stripeTokenType'),
            email=request.POST.get('stripeEmail'),
        )
        try:
            with transaction.atomic():
                charge_for_payment(stripe_payment)
                order.payment_date = date.today()
                order.save()
                create_invoices_for_order(order)
                # TODO send_confirmation_email()

                return redirect(
                    'cart:step5_congrats_order_complete', order_uuid=order.uuid
                )
        except PaymentError:
            # Redirect to the same page, show information about failed
            # payment(s) and reshow the same Pay with Card button
            return redirect('.')

    return TemplateResponse(
        request,
        "ep19/bs/cart/step_4_payment.html",
        {
            'order': order,
            'payments': payments,
            'total_for_stripe': total_for_stripe,
        },
    )


@login_required
@staff_member_required  # TEMPORARY for testing
def cart_step5_congrats_order_complete(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)
    return TemplateResponse(
        request,
        "ep19/bs/cart/step_5_congrats_order_complete.html",
        {'order': order},
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

    fares = fares.filter(code__regex=FARE_CODE_REGEXES["groups"][regex_group])

    return fares


class PersonalBillingForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['card_name', 'country', 'address', 'billing_notes']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'billing_notes': forms.Textarea(attrs={'rows': 3}),
        }


class BusinessBillingForm(forms.ModelForm):

    # address and country are required, vat_number may be not (or conditional,
    # for non-EU countries)

    class Meta:
        model = Order
        fields = [
            'card_name',
            'country',
            'address',
            'billing_notes',
            'vat_number',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'billing_notes': forms.Textarea(attrs={'rows': 3}),
        }


urlpatterns_ep19 = [
    url(r'^$', cart_step1_choose_type_of_order, name="step1_choose_type"),
    url(
        r'^(?P<type_of_tickets>\w+)/$',
        cart_step2_pick_tickets,
        name="step2_pick_tickets",
    ),
    url(
        r'^add-billing/(?P<order_uuid>[\w-]+)/$',
        cart_step3_add_billing_info,
        name="step3_add_billing_info",
    ),
    url(
        r'^payment/(?P<order_uuid>[\w-]+)/$',
        cart_step4_payment,
        name="step4_payment",
    ),
    url(
        r'^thanks/(?P<order_uuid>[\w-]+)/$',
        cart_step5_congrats_order_complete,
        name="step5_congrats_order_complete",
    ),
]
