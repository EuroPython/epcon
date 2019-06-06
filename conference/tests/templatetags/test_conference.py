import mock

from django.conf import settings
from django.template import Context
from django.test import RequestFactory
from django.test import TestCase

from conference.templatetags.conference import (
    conference_js_data, _lang, get_deadlines, conference_talks,
)
from tests.factories import (
    ConferenceFactory, ConferenceTagFactory, TalkFactory
)


class PrivateFunctionsTestCase(TestCase):
    def test_lang(self):
        request_factory = RequestFactory()
        request = request_factory.get('/hello')
        context = Context({'request': request})

        self.assertEqual(_lang(context), settings.LANGUAGE_CODE)

class ConferenceTemplateTagsTestCase(TestCase):
    @mock.patch('conference.templatetags.conference._lang', return_value='en')
    @mock.patch('conference.dataaccess.deadlines')
    def test_get_deadlines(self, mock_deadlines, mock_lang):

        mock_deadlines.return_value = [{'expired': False}]
        deadlines = get_deadlines(Context({}))
        self.assertEqual(len(deadlines), 1)

        mock_deadlines.return_value = [{'expired': True}]
        deadlines = get_deadlines(Context({}))
        self.assertEqual(len(deadlines), 0)

    @mock.patch('conference.dataaccess.talks_data')
    def test_conference_talks(self, mock_talks_data):
        conference = ConferenceFactory(code='epbeta')

        TalkFactory(conference=conference.code, status='accepted')
        TalkFactory(conference=conference.code, status='proposed')

        mock_talks_data.side_effect = lambda qs: list(qs)

        # FIXME: add a test for conference.dataaccess.talks_data
        talks = conference_talks(conference='epbeta')
        self.assertEqual(len(talks), 1)

    def test_conference_js_data(self):
        js_data = conference_js_data(tags={ConferenceTagFactory(): set()})

        self.assertTrue(isinstance(js_data, str))
