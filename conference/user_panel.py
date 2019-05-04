from datetime import timedelta

from django.conf.urls import url
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from django.contrib import messages
from django import forms
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.core.urlresolvers import reverse_lazy
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views

from conference.models import Speaker, TalkSpeaker, Conference, Ticket
from conference.tickets import assign_ticket_to_user, reset_ticket_settings
from assopy.models import Invoice, Order
from p3.models import TicketConference


@login_required
def user_dashboard(request):
    proposals = get_proposals_for_current_conference(request.user)
    orders = get_orders_for_current_conference(request.user)
    invoices = get_invoices_for_current_conference(request.user)
    tickets = get_tickets_for_current_conference(request.user)

    return TemplateResponse(
        request,
        "ep19/bs/user_panel/dashboard.html",
        {
            'proposals': proposals,
            'orders': orders,
            'invoices': invoices,
            "tickets": tickets,
        },
    )


@login_required
def manage_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        return HttpResponse("Can't do", status=403)

    ticket_configuration, _ = TicketConference.objects.get_or_create(
        ticket=ticket
    )

    ticket_configuration_form = TicketConfigurationForm(
        instance=ticket_configuration
    )

    if request.method == 'POST':
        ticket_configuration_form = TicketConfigurationForm(
            request.POST, instance=ticket_configuration
        )

        if ticket_configuration_form.is_valid():
            with transaction.atomic():
                ticket_configuration_form.save()
                messages.success(request, "Ticket configured!")
                return redirect("user_panel:dashboard")

    return TemplateResponse(
        request,
        "ep19/bs/user_panel/configure_ticket.html",
        {
            "ticket_configuration_form": ticket_configuration_form,
            'ticket': ticket,
        },
    )


@login_required
def assign_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        return HttpResponse("Can't do", status=403)

    assignment_form = AssignTicketForm()

    if request.method == 'POST':
        assignment_form = AssignTicketForm(request.POST)

        if assignment_form.is_valid():
            user = assignment_form.get_user()
            with transaction.atomic():
                assign_ticket_to_user(ticket, user)
                reset_ticket_settings(ticket)

            messages.success(
                request, "Ticket successfuly reassigned to %s" % user.email
            )
            return redirect("user_panel:dashboard")

    return TemplateResponse(
        request,
        "ep19/bs/user_panel/assign_ticket.html",
        {"ticket": ticket, "assignment_form": assignment_form},
    )


class AssignTicketForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        try:
            self.get_user()
        except User.DoesNotExist:
            raise forms.ValidationError(
                "Sorry, user does not exist in our system. "
                "Please ask them to create an account first"
            )

        return self.cleaned_data['email']

    def get_user(self):
        return User.objects.get(email=self.cleaned_data['email'])


class CommaStringMultipleChoiceField(forms.MultipleChoiceField):
    def to_python(self, value):
        return [val.rstrip().lstrip() for val in value.split(',')]

    def clean(self, value):
        return ",".join([val.rstrip().lstrip() for val in value])


class TicketConfigurationForm(forms.ModelForm):

    days = CommaStringMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(), required=False
    )

    class Meta:
        model = TicketConference
        fields = ['diet', 'shirt_size', 'tagline', 'days']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['days'].choices = self.conference_days()

    def conference_days(self):
        conference = Conference.objects.current()
        choices = []
        date = conference.conference_start
        while date <= conference.conference_end:
            choices.append((str(date), date.strftime("%A %d %B %Y")))
            date += timedelta(days=1)
        return choices


def get_tickets_for_current_conference(user):
    return Ticket.objects.filter(
        Q(orderitem__order___complete=True) & Q(user=user)
    )


def get_invoices_for_current_conference(user):
    return Invoice.objects.filter(
        # HACK
        emit_date__year=Conference.objects.current().conference_start.year
    )


def get_proposals_for_current_conference(user):
    """
    This goes through TalkSpeaker module, not Talk.created_by to correctly show
    cases if people are assigned (as co-speakers) to proposals/talks created by
    other people
    """

    try:
        speaker = user.speaker
    except Speaker.DoesNotExist:
        return None

    talkspeakers = TalkSpeaker.objects.filter(
        speaker=speaker, talk__conference=Conference.objects.current().code
    )

    return [ts.talk for ts in talkspeakers]


def get_orders_for_current_conference(user):
    # HACK(artcz) -- because Order doesn't have a link to Conference, we'll
    # just filter by current's conference year
    year = Conference.objects.current().conference_start.year
    return Order.objects.filter(created__year=year, user=user.assopy_user)


urlpatterns = [
    url(r"^$", user_dashboard, name="dashboard"),
    url(
        r"^manage-ticket/(?P<ticket_id>\d+)/$",
        manage_ticket,
        name="manage_ticket",
    ),
    url(
        r"^assign-ticket/(?P<ticket_id>\d+)/$",
        assign_ticket,
        name="assign_ticket",
    ),
    # Password change, using default django views.
    # TODO(artcz): Those are Removed in Django21 and we should replcethem with
    # class based PasswordChange{,Done}View
    url(
        r"^password/change/$",
        auth_views.password_change,
        kwargs={
            "template_name": "ep19/bs/user_panel/password_change.html",
            "post_change_redirect": reverse_lazy(
                "user_panel:password_change_done"
            ),
        },
        name="password_change",
    ),
    url(
        r"^password/change/done/$",
        auth_views.password_change_done,
        kwargs={
            "template_name": "ep19/bs/user_panel/password_change_done.html"
        },
        name="password_change_done",
    ),
]
