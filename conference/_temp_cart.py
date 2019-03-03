"""
Everything related to buying tickets on the website
"""

from django import forms
from django.conf import settings
from django.conf.urls import url
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from assopy.models import Coupon, Order, ENABLED_ORDER_PAYMENT, AssopyUser
from conference.models import Fare


ACCEPT_COC_AND_PRIVACY_POLICY_LABEL = (
    'I have read and accepted the '
    '<a href="/coc" target="blank">EuroPython 2018 Code of Conduct</a> '
    'as well as the '
    '<a href="/privacy" target="blank">EuroPython 2019 Privacy Policy</a>.'
)

COMPANY_BILLING_NOTES_HELP_TEXT = (
    "If your company needs some information to appear on the invoice "
    "in addition to those provided above (eg. PO number, etc.), "
    "write them here.<br />"
    "We reserve the right to review the contents of this box."
)


class BillingData(forms.ModelForm):

    payment = forms.ChoiceField(choices=ENABLED_ORDER_PAYMENT, initial="cc")
    code_conduct = forms.BooleanField(
        label=ACCEPT_COC_AND_PRIVACY_POLICY_LABEL
    )

    class Meta:
        model = AssopyUser
        exclude = ("user", "token", "assopy_id", "vat_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["card_name"].label = "Your Name"
        self.fields["country"].required = True
        self.fields["address"].required = True

    def clean_card_name(self):
        data = self.cleaned_data.get("card_name", "")

        if not data:
            return self.instance.name()

        else:
            return data


class BillingDataCompany(BillingData):
    billing_notes = forms.CharField(
        label="Additional billing information",
        help_text=COMPANY_BILLING_NOTES_HELP_TEXT,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = AssopyUser
        # TODO(artcz): Figure out what to exclude
        exclude = ('user', 'token', 'assopy_id', 'cf_code')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["card_name"].label = "Company Name"
        self.fields["address"].required = True


class FormTickets(forms.Form):
    coupon = forms.CharField(
        label="Insert your discount code and save money!",
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"size": 10}),
    )

    payment = forms.ChoiceField(
        choices=(("paypal", "PayPal"), ("bank", "Bank"))
    )
    order_type = forms.ChoiceField(
        choices=(
            ("non-deductible", "Personal Purchase"),
            ("deductible", "Company Purchase"),
        ),
        initial="non-deductible",
    )

    def __init__(self, *args, **kwargs):
        super(FormTickets, self).__init__(*args, **kwargs)

        for t in self.available_fares():
            field = forms.IntegerField(
                label=t.name, min_value=0, required=False
            )
            field.fare = t
            self.fields[t.code] = field

        self.user = kwargs.pop("user", None)

        # Deleting payment field because I want to delay this choice
        del self.fields["payment"]

    def available_fares(self):
        return Fare.objects.available()

    def clean_coupon(self):
        data = self.cleaned_data.get("coupon", "").strip()

        if not data:
            return None

        if data[0] == "_":
            raise forms.ValidationError("invalid coupon")

        try:
            coupon = Coupon.objects.get(
                conference=settings.CONFERENCE_CONFERENCE, code__iexact=data
            )

        except Coupon.DoesNotExist:
            raise forms.ValidationError("invalid coupon")

        if not coupon.valid(self.user):
            raise forms.ValidationError("invalid coupon")

        return coupon

    def clean(self):
        fares = dict((x.code, x) for x in self.available_fares())
        data = self.cleaned_data
        o = []
        total = 0

        for k, q in data.items():

            if k not in fares:
                continue

            if not q:
                continue

            total += q
            f = fares[k]

            if not f.valid():
                self._errors[k] = self.error_class(["Invalid fare"])
                del data[k]
                continue
            o.append((f, {"qty": q}))

        data["tickets"] = o

        company = data.get("order_type") == "deductible"

        for ix, row in list(enumerate(data["tickets"]))[::-1]:
            fare = row[0]

            if fare.ticket_type != "company":
                continue

            if company ^ (fare.code[-1] == "C"):
                del data["tickets"][ix]
                del data[fare.code]

        for fname in ("bed_reservations", "room_reservations"):
            for r in data.get(fname, []):
                data["tickets"].append(
                    (
                        Fare.objects.get(
                            conference=settings.CONFERENCE_CONFERENCE,
                            code=r["fare"],
                        ),
                        r,
                    )
                )

        if not data["tickets"]:
            raise forms.ValidationError("No tickets")

        return data


def cart(request):
    user = None

    if request.user.is_authenticated:
        try:
            user = request.user.assopy_user

        except AttributeError:
            pass

    account_type = "p"

    # user-cart is needed for the confirmation page with invoce data,
    # I want to be suer that the only way to set it is when there is
    # a valid POST request
    request.session.pop("user-cart", None)
    if request.method == "POST":

        if not request.user.is_authenticated:
            return redirect("p3-cart")

        form = FormTickets(data=request.POST, user=user)

        if form.is_valid():
            request.session["user-cart"] = form.cleaned_data
            return redirect("p3-billing")

    else:
        order_type = "deductible" if account_type == "c" else "non-deductible"
        form = FormTickets(initial={"order_type": order_type}, user=user)

    fares = {}

    for f in form.available_fares():
        if not f.code.startswith("_"):
            fares[f.code] = f

    fares_ordered = sorted(list(fares.values()), key=lambda x: x.name)

    return TemplateResponse(request, "cart/cart.html", {
        "form": form,
        "fares": fares,
        "fares_ordered": fares_ordered,
        "account_type": account_type,
    })


@login_required
def calculator(request):
    output = {"tickets": [], "coupon": 0, "total": 0}
    if request.method == "POST":
        form = FormTickets(data=request.POST, user=request.user.assopy_user)
        if not form.is_valid():
            # if the fom is not validate because of the coupon I'm deleting it
            # from the data to be able to give the user a feedback anyway
            if "coupon" in form.errors:
                qdata = request.POST.copy()
                del qdata["coupon"]
                form = FormTickets(data=qdata, user=request.user.assopy_user)

        if form.is_valid():
            data = form.cleaned_data
            coupons = []
            if data["coupon"]:
                coupons.append(data["coupon"])
            totals = Order.calculator(
                items=data["tickets"],
                coupons=coupons,
                user=request.user.assopy_user,
            )

            # NOTE(artcz)(2018-09-05) this was related to hotel bookings. left
            # here for compatibility below. probably not needed and can be
            # removed
            booking = None

            def _fmt(x):
                if x == 0:
                    # x is a Decimal and 0 and -0 are different
                    return "0"
                else:
                    return "%.2f" % x

            grand_total = 0
            # to allow the client to associate each ticket with the correct
            # price infos are rewritten inthe same "format" that has been used
            # to send them.
            tickets = []
            for row in totals["tickets"]:
                fcode = row[0].code
                total = row[2]
                params = row[1]
                if "period" in params:
                    start = booking.booking_start
                    params["period"] = [
                        (x - start).days for x in params["period"]
                    ]
                tickets.append((fcode, params, _fmt(total)))
                grand_total += total
            output["tickets"] = tickets

            if data["coupon"]:
                total = totals["coupons"][data["coupon"].code][0]
                output["coupon"] = _fmt(total)
                grand_total += total

            output["total"] = _fmt(grand_total)
        else:
            return JsonResponse({
                'errors': form.errors
            })

    return JsonResponse(output)


@login_required
def billing(request):
    try:
        tickets = request.session["user-cart"]["tickets"]
    except KeyError:
        # the session is missing the user-cart key, instead of raising a
        # 500 error I'm sending back the user to the cart.
        return redirect("p3-cart")

    recipient = "p"
    conference_recipients = set()

    for fare, foo in tickets:

        if fare.recipient_type == "c":
            recipient = "c"

        if fare.ticket_type == "conference":
            # you cannot buy tickets for different entity types (user/company)
            conference_recipients.add(
                "c" if fare.recipient_type == "c" else "p"
            )

    if len(conference_recipients) > 1:
        raise ValueError(
            "mismatched fares: %s" % ",".join(x[0].code for x in tickets)
        )

    if recipient == "p":
        cform = BillingData

    else:
        cform = BillingDataCompany

    coupon = request.session["user-cart"]["coupon"]
    totals = Order.calculator(
        items=tickets,
        coupons=[coupon] if coupon else None,
        user=request.user.assopy_user,
    )

    if request.method == "POST":
        auser = request.user.assopy_user
        post_data = request.POST.copy()

        order_data = None
        if totals["total"] == 0:
            # free order, I'm only interested in knowing the user accepted the
            # code of conduct.
            if "code_conduct" in request.POST:
                order_data = {"payment": "bank"}
            else:
                # if it wasn't accepted the form is prepared and the user
                # will see the checkbox in red
                form = cform(instance=auser, data=post_data)
                form.is_valid()

        else:
            form = cform(instance=auser, data=post_data)
            if form.is_valid():
                order_data = form.cleaned_data
                form.save()

        if order_data:
            coupon = request.session["user-cart"]["coupon"]
            kw = dict(
                user=auser,
                payment=order_data["payment"],
                billing_notes=order_data.get("billing_notes", ""),
                items=request.session["user-cart"]["tickets"],
                coupons=[coupon] if coupon else None,
            )

            if recipient == "p":
                kw["cf_code"] = auser.cf_code

            else:
                kw["vat_number"] = auser.vat_number

            o = Order.objects.create(**kw)

            if totals["total"] == 0:
                # Nothing to pay, complete order and we're done
                o.confirm_order(o.created)
                o.complete()
                return redirect('assopy-tickets')

            if settings.STRIPE_ENABLED and order_data["payment"] == "cc":
                return redirect("assopy-stripe-checkout", pk=o.pk)

            elif order_data["payment"] in ("paypal", "cc"):
                urlname = (
                    "assopy-paypal-redirect"
                    if order_data["payment"] == "paypal"
                    else "assopy-cc-paypal-redirect"
                )

                return redirect(
                    urlname,
                    kwargs={"code": str(o.code).replace("/", "-")}
                )

            elif o.payment_url:
                return redirect(o.payment_url)

            else:
                return redirect(
                    "assopy-bank-feedback-ok",
                    kwargs={"code": o.code.replace("/", "-")},
                )

    else:
        auser = request.user.assopy_user

        if not auser.card_name:
            auser.card_name = "%s %s" % (
                request.user.first_name,
                request.user.last_name,
            )

        form = cform(instance=auser)

    return TemplateResponse(request, "cart/billing.html", {
        "totals": totals,
        "form": form
    })


urlpatterns = [
    url(r'^cart/$', cart, name='cart'),
    url(r'^cart/calculator/$', calculator, name='calculator'),
    url(r'^billing/$', billing, name='billing'),
]
