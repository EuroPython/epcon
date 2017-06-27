import datetime

import mock
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings, RequestFactory

from conference.tests.factories.conference import ConferenceFactory


class TestLiveViews(TestCase):
    @override_settings(CONFERENCE='epbeta', DEBUG=False)
    def test_live_conference(self):
        tmp = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())
        from p3.views.live import _live_conference

        conf, _ = _live_conference()

        self.assertEqual(tmp, conf)

    @override_settings(CONFERENCE='epbeta', DEBUG=False)
    @mock.patch('django.shortcuts.render')
    def test_live(self, mock_render):
        tmp = ConferenceFactory(code='epbeta', conference_start=datetime.date.today())

        request_factory = RequestFactory()

        url = reverse('p3-live')
        request = request_factory.get(url)

        from p3.views.live import live

        live(request)
        self.assertTrue(mock_render.called)

        request, template, context = mock_render.call_args[0]


        self.assertEqual(context['tracks'].count(), 0)
        self.assertTrue(template, 'p3/live.html')
