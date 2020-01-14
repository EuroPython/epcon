from django.test import TestCase

from conference.templatetags.conference import conference_js_data
from tests.factories import ConferenceTagFactory


class ConferenceTemplateTagsTestCase(TestCase):

    def test_conference_js_data(self):
        js_data = conference_js_data(tags={ConferenceTagFactory(): set()})

        self.assertTrue(isinstance(js_data, str))
