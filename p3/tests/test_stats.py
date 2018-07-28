import mock
from django.test import TestCase
from django_factory_boy import auth as auth_factories

from assopy.stripe.tests.factories import (
    OrderItemFactory,
    AssopyUserFactory,
    VatFactory
)
from assopy.tests.factories.order import CreditCardOrderFactory
from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.fare import TicketFactory, FareFactory
from p3.tests.factories.ticket_conference import TicketConferenceFactory
from p3.models import TICKET_CONFERENCE_SHIRT_SIZES, TICKET_CONFERENCE_DIETS

from p3.stats import shirt_sizes, diet_types


class StatsTestCase(TestCase):
    def setUp(self):
        self.conference = ConferenceFactory()
        self.user = auth_factories.UserFactory()
        self.assopy_user = AssopyUserFactory(user=self.user)

    def test_creation_option(self):
        from p3.stats import _create_option
        total_qs = mock.Mock()
        total_qs.count.return_value = 1
        output = _create_option('id', 'title', total_qs)
        self.assertDictEqual(output, {
            'id': 'id',
            'title': 'title',
            'total': 1,
        })

    def test_tickets(self):
        from p3.stats import _tickets
        tickets = _tickets(self.conference)

    def test_assigned_tickets(self):
        from p3.stats import _assigned_tickets
        tickets = _assigned_tickets(self.conference)

    def test_unassigned_tickets(self):
        from p3.stats import _unassigned_tickets
        tickets = _unassigned_tickets(self.conference)

    @mock.patch('email_template.utils.email')
    @mock.patch('django.core.mail.send_mail')
    def test_shirt_sizes(self, mock_send_email, mock_email):
        fare = FareFactory(conference=self.conference, ticket_type='conference')

        ticket = TicketFactory(fare=fare, user=self.user, frozen=False)

        ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=self.user.email)
        order = CreditCardOrderFactory(user=self.assopy_user)
        vat = VatFactory()
        order._complete = True
        order.save()
        order_item = OrderItemFactory(order=order, ticket=ticket, price=1, vat=vat)

        repartition = shirt_sizes(self.conference)
        assert repartition[0] == {
            'total': 1,
            'title': dict(TICKET_CONFERENCE_SHIRT_SIZES)[ticket_conference.shirt_size],
        }

    @mock.patch('email_template.utils.email')
    @mock.patch('django.core.mail.send_mail')
    def test_diet_types(self, mock_send_email, mock_email):
        fare = FareFactory(conference=self.conference, ticket_type='conference')

        ticket = TicketFactory(fare=fare, user=self.user, frozen=False)
        ticket_conference = TicketConferenceFactory(ticket=ticket, assigned_to=self.user.email)
        order = CreditCardOrderFactory(user=self.assopy_user)

        vat = VatFactory()
        order._complete = True
        order.save()
        order_item = OrderItemFactory(order=order, ticket=ticket, price=1, vat=vat)

        repartition = diet_types(self.conference)
        assert repartition[0] == {
            'total': 1,
            'title': dict(TICKET_CONFERENCE_DIETS)[ticket_conference.diet],
        }

    def test_presence_days(self):
        from p3.stats import presence_days
        repartition = presence_days(self.conference)

    def test_tickets_status(self):
        from p3.stats import tickets_status
        repartition = tickets_status(self.conference)

    def test_speaker_status(self):
        from p3.stats import speaker_status
        repartition = speaker_status(self.conference)

    def test_conference_speakers(self):
        from p3.stats import conference_speakers
        repartition = conference_speakers(self.conference)

    def test_conference_speakers_day(self):
        from p3.stats import conference_speakers_day
        repartition = conference_speakers_day(self.conference)

    def test_pp_tickets(self):
        from p3.stats import pp_tickets
        repartition = pp_tickets(self.conference)
