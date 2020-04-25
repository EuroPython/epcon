from datetime import timedelta

import pytest

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from conference.models import TALK_STATUS, TALK_LEVEL
from p3.templatetags import sessions
from tests.factories import UserFactory, TalkFactory, ConferenceTagFactory, TalkSpeakerFactory, SpeakerFactory
from tests.common_tools import get_default_conference, redirects_to, template_used, make_user

pytestmark = [pytest.mark.django_db]


def test_spealers_templatetag():
    names = [
        # these 2 should not be listed
        ("To Be", "Announced"),
        ("Tobey", "Announced"),
        # these 2 should be groupped under D
        ("Dan", "Schmoe"),
        ("Đan", "Again"),
        # these 2 should be groupped under A
        ("Anna", "Doe"),
        ("Ändy", "Unicode"),
    ]
    conf = get_default_conference()
    speakers = [
        TalkSpeakerFactory(
            speaker__user=make_user(first_name=f_name, last_name=l_name),
            talk__status='accepted',
        )
        for (f_name, l_name) in names
    ]
    data = sessions.speakers(conf.code)
    assert set(data['groups'].keys()) == {'A', 'D'}
    assert [s['fullname'] for s in data['groups']['D']] == ["Đan Again", "Dan Schmoe"]
    assert [s['fullname'] for s in data['groups']['A']] == ["Ändy Unicode", "Anna Doe"]
