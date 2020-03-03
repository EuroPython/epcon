from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.urls import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils import timezone

from conference.models import StripePayment, Ticket

from .fares import (
    FARE_CODE_GROUPS,
    FARE_CODE_REGEXES,
    FARE_TICKET_TYPES,
    FARE_CODE_TYPES,
    FareIsNotAvailable,
    get_available_fares,
    is_fare_code_valid,
    disable_early_bird_fares,
)
from .invoicing import create_invoices_for_order
from .orders import (
    Order,
    OrderCalculation,
    calculate_order_price_including_discount,
    create_order,
    is_business_order,
    is_non_conference_ticket_order,
)
from .payments import PaymentError, prepare_for_payment, verify_payment
from .decorators import full_profile_required


GLOBAL_MAX_PER_FARE_TYPE = 6
ORDER_CONFIRMATION_EMAIL_SUBJECT = "EuroPython2020: Order confirmation"


@full_profile_required
def cart_step1_choose_type_of_order(request):
    """
    This view is not login required because we want to display some summary of
    ticket prices here as well.
    """
    special_fares = get_available_fares_for_type(TicketType.other)
    context = {"show_special": bool(special_fares)}
    return TemplateResponse(
        request, "conference/cart/step_1_choose_type_of_order.html", context
    )


@login_required
@full_profile_required
def cart_step2_pick_tickets(request, type_of_tickets):
    """
    Only submit this form if user is authenticated, otherwise display some
    support info.
    """

    assert type_of_tickets in TicketType.ALL

    available_fares = get_available_fares_for_type(type_of_tickets)
    context = {
        "CartActions": CartActions,
        "available_fares": available_fares,
        "global_max_per_fare_type": GLOBAL_MAX_PER_FARE_TYPE,
        "calculation": OrderCalculation(0, 0, 0),  # empty calculation
        "currency": "EUR",
        "fares_info": {},  # empty fares info
    }
    if request.method == "POST":

        discount_code, fares_info = extract_order_parameters_from_request(
            request.POST
        )
        context["fares_info"] = fares_info

        if sum(fares_info.values()) == 0:
            messages.error(request, "Please select some tickets :)")
            return redirect(".")

        try:
            calculation, coupon = calculate_order_price_including_discount(
                for_user=request.user,
                for_date=timezone.now().date(),
                fares_info=fares_info,
                discount_code=discount_code,
            )
        except FareIsNotAvailable:
            messages.error(request, "A selected fare is not available")
            return redirect(".")

        if CartActions.apply_discount_code in request.POST:
            context["calculation"] = calculation
            context["discount_code"] = discount_code or "No discount code"
            if discount_code and not coupon:
                messages.warning(
                    request, "The discount code provided expired or is invalid"
                )

        elif CartActions.buy_tickets in request.POST:
            order = create_order(
                for_user=request.user,
                for_date=timezone.now().date(),
                fares_info=fares_info,
                calculation=calculation,
                order_type=type_of_tickets,
                coupon=coupon,
            )
            return redirect(
                "cart:step3_add_billing_info", order_uuid=order.uuid
            )

    return TemplateResponse(
        request, "conference/cart/step_2_pick_tickets.html", context
    )


@login_required
@full_profile_required
def cart_step3_add_billing_info(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)

    if is_business_order(order) or is_non_conference_ticket_order(order):
        billing_form = BusinessBillingForm
    else:
        billing_form = PersonalBillingForm

    form = billing_form(instance=order)

    if request.method == "POST":
        form = billing_form(data=request.POST, instance=order)

        if form.is_valid():
            form.save()
            return redirect("cart:step4_payment", order_uuid=order.uuid)

    return TemplateResponse(
        request,
        "conference/cart/step_3_add_billing_info.html",
        {"form": form, "order": order},
    )


@login_required
@full_profile_required
def cart_step4_payment(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)
    total_for_stripe = int(order.total() * 100)
    payments = order.stripepayment_set.all().order_by("created")

    if request.method == "POST":

        if total_for_stripe == 0:
            # For 100% discounted orders/coupons
            order.payment_date = timezone.now()
            order.save()

            with transaction.atomic():
                create_invoices_for_order(order)
                current_site = get_current_site(request)
                send_order_confirmation_email(order, current_site)

            return redirect(
                "cart:step5_congrats_order_complete", order_uuid=order.uuid
            )

    # sanity/security check to make sure we don't publish the the wrong key
    stripe_key = settings.STRIPE_PUBLISHABLE_KEY
    assert stripe_key.startswith("pk_")
    stripe_session_id = None
    if total_for_stripe > 0:
        stripe_session = prepare_for_payment(
            request,
            order = order,
            description = f"payment for order {order.pk} by {request.user.email}"
        )
        stripe_session_id = stripe_session.id

    return TemplateResponse(
        request,
        "conference/cart/step_4_payment.html",
        {
            "order": order,
            "payment": payments,
            "stripe_key": stripe_key,
            "total_for_stripe": total_for_stripe,
            "stripe_session_id": stripe_session_id,
        },
    )


@login_required
def cart_step4b_verify_payment(request, payment_uuid, session_id):
    payment = get_object_or_404(StripePayment, uuid=payment_uuid)
    order = payment.order
    if payment.status != 'SUCCESSFUL':
        try:
            verify_payment(payment, session_id)
        except PaymentError:
            return redirect("cart:step4_payment", order_uuid=order.uuid)

        if order.payment_date is not None:
            # XXX This order was already paid for(!)
            payment.message = 'Duplicate payment?!?'
            payment.save()
        else:
            order.payment_date = timezone.now()
            order.save()

            with transaction.atomic():
                create_invoices_for_order(order)
                current_site = get_current_site(request)
                send_order_confirmation_email(order, current_site)

        handle_early_bird_ticket_limit()

    return redirect("cart:step5_congrats_order_complete", order.uuid)


@login_required
def cart_step5_congrats_order_complete(request, order_uuid):
    order = get_object_or_404(Order, uuid=order_uuid)

    return TemplateResponse(
        request,
        "conference/cart/step_5_congrats_order_complete.html",
        {"order": order},
    )


def extract_order_parameters_from_request(post_data):
    discount_code = None
    fares_info = {}

    for k, v in post_data.items():
        if k == "discount_code":
            discount_code = v

        elif is_fare_code_valid(k):
            try:
                fares_info[k] = int(v)
            except ValueError:
                pass

    return discount_code, fares_info


def send_order_confirmation_email(order: Order, current_site) -> None:

    user_panel_path = reverse("user_panel:dashboard")
    user_panel_url = f"https://{current_site.domain}{user_panel_path}"

    content = render_to_string(
        "conference/emails/order_confirmation_email.txt",
        {"order": order, "user_panel_url": user_panel_url},
    )

    send_mail(
        subject=ORDER_CONFIRMATION_EMAIL_SUBJECT,
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.user.email],
    )


def handle_early_bird_ticket_limit():
    eb_ticket_orders = Ticket.objects.filter(
        fare__conference=settings.CONFERENCE_CONFERENCE,
        frozen=False,
        # orderitem__order___complete=True,
        fare__code__regex=FARE_CODE_REGEXES["types"][FARE_CODE_TYPES.EARLY_BIRD]
    )

    if eb_ticket_orders.count() > settings.EARLY_BIRD_ORDER_LIMIT:
        disable_early_bird_fares()


class TicketType:
    """
    NOTE(artcz): This should be in sync with assopy/models.py::ORDER_TYPE
    """
    personal = "personal"
    company = "company"
    student = "student"
    other = "other"

    CONFERENCE_OR_TRAINING = [personal, company, student]
    ALL = [personal, company, student, other]


class CartActions:
    apply_discount_code = "apply_discount_code"
    buy_tickets = "buy_tickets"


# TODO: move to fares
def get_available_fares_for_type(type_of_tickets):
    assert type_of_tickets in TicketType.ALL

    fares = get_available_fares(timezone.now().date())

    if type_of_tickets in TicketType.CONFERENCE_OR_TRAINING:

        if type_of_tickets == TicketType.personal:
            regex_group = FARE_CODE_GROUPS.PERSONAL

        if type_of_tickets == TicketType.company:
            regex_group = FARE_CODE_GROUPS.COMPANY

        if type_of_tickets == TicketType.student:
            regex_group = FARE_CODE_GROUPS.STUDENT

        fares = fares.filter(
            code__regex=FARE_CODE_REGEXES["groups"][regex_group]
        )

    elif type_of_tickets == TicketType.other:
        fares = fares.exclude(
            ticket_type=FARE_TICKET_TYPES.conference,
        )

    return fares


class PersonalBillingForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["card_name", "country", "address"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"card_name": "Name of the buyer"}


class BusinessBillingForm(forms.ModelForm):

    # address and country are required, vat_number may be not (or conditional,
    # for non-EU countries)

    class Meta:
        model = Order
        fields = [
            "card_name",
            "country",
            "address",
            "billing_notes",
            "vat_number",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "billing_notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"card_name": "Name of the buyer"}


urlpatterns = [
    url(r"^$", cart_step1_choose_type_of_order, name="step1_choose_type"),
    url(
        r"^(?P<type_of_tickets>\w+)/$",
        cart_step2_pick_tickets,
        name="step2_pick_tickets",
    ),
    url(
        r"^add-billing/(?P<order_uuid>[\w-]+)/$",
        cart_step3_add_billing_info,
        name="step3_add_billing_info",
    ),
    url(
        r"^payment/(?P<order_uuid>[\w-]+)/$",
        cart_step4_payment,
        name="step4_payment",
    ),
    url(
        r"^verify/(?P<payment_uuid>[\w-]+)/(?P<session_id>[-_\w{}]+)/$",
        cart_step4b_verify_payment,
        name="step4b_verify_payment",
    ),
    url(
        r"^thanks/(?P<order_uuid>[\w-]+)/$",
        cart_step5_congrats_order_complete,
        name="step5_congrats_order_complete",
    ),
]
