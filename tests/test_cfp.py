from datetime import timedelta

from pytest import mark
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from conference.models import Conference, Talk, TALK_TYPE_CHOICES, TALK_LEVEL
from conference.cfp import (
    dump_relevant_talk_information_to_dict,
    AddSpeakerToTalkForm,
)
try:
    from pycon.settings import CONFERENCE_TIMESLOTS
except ImportError:
    CONFERENCE_TIMESLOTS = None

from tests.common_tools import redirects_to, template_used
from tests.factories import TalkFactory

pytestmark = mark.django_db


@mark.parametrize(
    "url",
    [
        reverse("cfp:step1_submit_proposal"),
        # using some random uuid because we just need to resolve url
        reverse("cfp:step2_add_speakers", args=["ABCDEFI"]),
        reverse("cfp:step3_thanks", args=["ABCDEFI"]),
        reverse("cfp:update", args=["ABCDEFI"]),
        reverse("cfp:update_speakers", args=["ABCDEFI"]),
    ],
)
def test_if_cfp_pages_are_login_required(client, url):
    response = client.get(url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


@mark.parametrize(
    "url",
    [
        reverse("cfp:step1_submit_proposal"),
        # using some random uuid because we just need to resolve url
        reverse("cfp:step2_add_speakers", args=["ABCDEFI"]),
        reverse("cfp:step3_thanks", args=["ABCDEFI"]),
        reverse("cfp:update", args=["ABCDEFI"]),
        reverse("cfp:update_speakers", args=["ABCDEFI"]),
    ],
)
def test_cfp_requires_full_profile_data(user_client, url):
    user = user_client.user
    attendee_profile = user.attendeeprofile
    attendee_profile.gender = ""
    attendee_profile.save()
    attendee_profile.refresh_from_db()

    response = user_client.get(url)
    assert response.status_code == 302
    assert response.url == reverse("user_panel:profile_settings")


def test_if_cfp_pages_are_unavailable_if_cfp_is_undefined(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "conference/cfp/cfp_is_closed.html")


def test_if_cfp_pages_are_unavailable_if_cfp_is_in_the_future(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() + timedelta(days=2),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "conference/cfp/cfp_is_closed.html")


def test_if_cfp_pages_are_unavailable_if_cfp_is_in_the_past(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() - timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "conference/cfp/cfp_is_closed.html")


def test_if_cfp_pages_are_available_if_cfp_is_active(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "conference/cfp/step1_talk_info.html")


def test_validation_errors_are_handled_on_step1(user_client):
    """
    NOTE(artcz)
    This test is basically a placholder to get a proper branch coverage.
    We should also (separately?) test if the validation itslef is correct.
    """
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")
    response = user_client.post(step1_url, {})
    # POST rerenders the same template
    assert template_used(response, "conference/cfp/step1_talk_info.html")


def test_if_user_can_submit_talk_details_and_is_redirect_to_step2(user_client):
    STEP1_CORRECT_REDIRECT_302 = 302

    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    data = {
        "type": TALK_TYPE_CHOICES.t_30,
        "abstract": "Abstract goes here",
        "title": "A title",
        "sub_title": "A sub title",
        "abstract_short": "Short abstract",
        "abstract_extra": "Abstract _extra",
        "tags": "abc, defg",
        "level": TALK_LEVEL.beginner,
        "domain_level": TALK_LEVEL.advanced,
    }
    if CONFERENCE_TIMESLOTS and \
       isinstance(CONFERENCE_TIMESLOTS, (list, tuple)):
        data['availability'] = [CONFERENCE_TIMESLOTS[0][0], ]

    response = user_client.post(step1_url, data)
    assert response.status_code == STEP1_CORRECT_REDIRECT_302

    talk = Talk.objects.get()
    talk_dict = dump_relevant_talk_information_to_dict(talk)
    assert talk_dict["type"] == TALK_TYPE_CHOICES.t_30
    assert talk_dict["type_display"] == "Talk (30 mins)"
    assert talk_dict["subtitle"] == "A sub title"
    assert talk_dict["abstract"] == "Abstract goes here"
    assert talk_dict["abstract_short"] == "Short abstract"
    assert talk_dict["abstract_extra"] == "Abstract _extra"
    assert talk_dict["python_level"] == "Beginner"
    assert talk_dict["domain_level"] == "Advanced"
    assert talk_dict["speakers"] == []
    if 'availability' in data:
        assert talk_dict['availability'] == data['availability']

    assert redirects_to(
        response, reverse("cfp:step2_add_speakers", args=[talk.uuid])
    )


@mark.skipif(CONFERENCE_TIMESLOTS is None, reason='no timeslot defined')
def test_if_user_cannot_submit_talk_if_availability_not_selected(user_client):
    STEP1_VALIDATION_FAIL_200 = 200

    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.post(
        step1_url,
        {
            "type": TALK_TYPE_CHOICES.t_30,
            "abstract": "Abstract goes here",
            "title": "A title",
            "sub_title": "A sub title",
            "abstract_short": "Short abstract",
            "abstract_extra": "Abstract _extra",
            "tags": "abc, defg",
            "level": TALK_LEVEL.beginner,
            "domain_level": TALK_LEVEL.advanced,
        },
    )

    assert response.status_code == STEP1_VALIDATION_FAIL_200


def test_if_user_cannot_submit_talk_if_release_not_selected(user_client):
    STEP1_VALIDATION_FAIL_200 = 200

    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.post(
        step1_url,
        {
            "type": TALK_TYPE_CHOICES.t_30,
            "abstract": "Abstract goes here",
            "title": "A title",
            "sub_title": "A sub title",
            "abstract_short": "Short abstract",
            "abstract_extra": "Abstract _extra",
            "tags": "abc, defg",
            "level": TALK_LEVEL.beginner,
            "domain_level": TALK_LEVEL.advanced,
        },
    )

    assert response.status_code == STEP1_VALIDATION_FAIL_200


def test_validation_errors_are_handled_on_step2(user_client):
    """
    NOTE(artcz)
    This test is basically a placholder to get a proper branch coverage.
    We should also (separately?) test if the validation itslef is correct.
    """
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    talk = TalkFactory()
    step2_url = reverse("cfp:step2_add_speakers", args=[talk.uuid])
    response = user_client.post(step2_url, {})
    # POST rerenders the same template
    assert template_used(response, "conference/cfp/step2_add_speaker.html")


def test_if_user_can_add_a_speaker_to_a_proposal(user_client):
    create_conference_with_open_cfp()
    STEP2_CORRECT_REDIRECT_302 = 302

    talk = TalkFactory()
    talk.setAbstract(
        "Setting abstract just because we'll need it to dump later"
    )
    step2_url = reverse("cfp:step2_add_speakers", args=[talk.uuid])

    response = user_client.get(step2_url)
    assert template_used(response, "conference/cfp/step2_add_speaker.html")

    response = user_client.post(
        step2_url,
        {
            "users_given_name": "Joe",
            "users_family_name": "Doe",
            "phone": "+48523456789",
            "bio": "ASdf bio",
            "i_accept_speaker_release": True
        },
    )
    assert response.status_code == STEP2_CORRECT_REDIRECT_302

    talk.refresh_from_db()
    talk_dict = dump_relevant_talk_information_to_dict(talk)
    speaker = talk_dict["speakers"][0]
    assert speaker["name"] == "Joe Doe"
    assert speaker["company"] == ""
    assert speaker["company_homepage"] == ""
    assert speaker["bio"] == "ASdf bio"
    assert speaker["phone"] == "+48523456789"


    assert redirects_to(
        response, reverse("cfp:step3_thanks", args=[talk.uuid])
    )


def test_if_correct_thanks_page_is_rendered(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    step3_url = reverse("cfp:step3_thanks", args=[talk.uuid])

    response = user_client.get(step3_url)
    assert template_used(response, "conference/cfp/step3_thanks.html")


def test_thanks_page_contains_link_to_preview_proposal(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    step3_url = reverse("cfp:step3_thanks", args=[talk.uuid])

    preview_link = reverse("cfp:preview", args=[talk.slug])
    response = user_client.get(step3_url)

    assert preview_link in response.content.decode()


def test_preview_page_renders_correct_content(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("Some abstract")
    preview_url = reverse("cfp:preview", args=[talk.slug])

    response = user_client.get(preview_url)
    assert talk.title in response.content.decode()
    assert talk.sub_title in response.content.decode()
    assert talk.getAbstract().body in response.content.decode()
    assert talk.abstract_short in response.content.decode()
    assert talk.abstract_extra in response.content.decode()


def test_preview_page_contains_edit_links_if_cfp_is_open_and_user_is_author(
    user_client
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])
    speaker_edit_link = reverse("cfp:update_speakers", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link in response.content.decode()
    assert speaker_edit_link in response.content.decode()


def test_preview_page_doesnt_contain_edit_link_if_cfp_is_open_but_user_is_not_author(  # NOQA
    user_client
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])
    speaker_edit_link = reverse("cfp:update_speakers", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link not in response.content.decode()
    assert speaker_edit_link not in response.content.decode()


def test_preview_page_doesnt_contain_edit_link_if_cfp_is_closed_and_user_is_author(  # NOQA
    user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() - timedelta(days=1),
    )
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])
    speaker_edit_link = reverse("cfp:update_speakers", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link not in response.content.decode()
    assert speaker_edit_link not in response.content.decode()


def test_regular_user_cant_access_program_wg_download(user_client):
    LOGIN_REQUIRED_302 = 302
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )
    url = reverse("cfp:program_wg_download_all_talks")
    response = user_client.get(url)
    assert response.status_code == LOGIN_REQUIRED_302
    assert redirects_to(response, "/admin/login/")


def test_admin_user_can_access_program_wg_download(admin_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )
    url = reverse("cfp:program_wg_download_all_talks")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == {"talks": []}


@mark.parametrize(
    "page_name, template",
    [
        ("cfp:update", "conference/cfp/update_proposal.html"),
        ("cfp:update_speakers", "conference/cfp/update_speakers.html"),
    ],
)
def test_update_pages_work_if_cfp_is_open_and_user_is_author(
    user_client,
    page_name,
    template
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()
    edit_url = reverse(page_name, args=[talk.uuid])

    response = user_client.get(edit_url)

    assert response.status_code == 200
    assert template_used(response, template)


@mark.parametrize(
    "page_name",
    [
        "cfp:update",
        "cfp:update_speakers",
    ],
)
def test_update_pages_dont_work_if_cfp_is_open_but_user_is_not_author(
    user_client, page_name,
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    edit_url = reverse(page_name, args=[talk.uuid])

    response = user_client.get(edit_url)
    assert response.status_code == 403


def test_preview_page_doesnt_work_if_cfp_is_closed_and_user_is_author(
    user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() - timedelta(days=1),
    )
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()
    edit_url = reverse("cfp:update", args=[talk.uuid])

    response = user_client.get(edit_url)
    assert response.status_code == 403


def test_validation_errors_are_handled_on_update_proposal(user_client):
    """
    NOTE(artcz)
    This test is basically a placholder to get a proper branch coverage.
    We should also (separately?) test if the validation itslef is correct.
    """
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()
    update_url = reverse("cfp:update", args=[talk.uuid])
    response = user_client.post(update_url, {})

    # POST rerenders the same template
    assert template_used(response, "conference/cfp/update_proposal.html")


def test_update_proposal_updates_proposal(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()

    edit_url = reverse("cfp:update", args=[talk.uuid])

    data = {
        "type": TALK_TYPE_CHOICES.t_45,
        "abstract": "New abstract",
        "abstract_short": "New short abstract",
        "abstract_extra": "New extra abstract",
        "level": TALK_LEVEL.intermediate,
        "domain_level": TALK_LEVEL.advanced,
        "title": "New title",
        "sub_title": "New sub title",
        "tags": "Some, tags",
    }
    if CONFERENCE_TIMESLOTS and \
       isinstance(CONFERENCE_TIMESLOTS, (list, tuple)):
        data['availability'] = [CONFERENCE_TIMESLOTS[0][0], ]

    response = user_client.post(edit_url, data)

    assert response.status_code == 302
    talk.refresh_from_db()

    assert redirects_to(response, reverse("cfp:preview", args=[talk.slug]))

    talk_dict = dump_relevant_talk_information_to_dict(talk)
    assert talk_dict["type"] == TALK_TYPE_CHOICES.t_45
    assert talk_dict["type_display"] == "Talk (45 mins)"
    assert talk_dict["subtitle"] == "New sub title"
    assert talk_dict["abstract"] == "New abstract"
    assert talk_dict["abstract_short"] == "New short abstract"
    assert talk_dict["abstract_extra"] == "New extra abstract"
    assert talk_dict["python_level"] == "Intermediate"
    assert talk_dict["domain_level"] == "Advanced"
    assert talk_dict["speakers"] == []


def test_update_proposal_fails_if_missing_release_agreement(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()

    edit_url = reverse("cfp:update", args=[talk.uuid])

    response = user_client.post(
        edit_url,
        {
            "type": TALK_TYPE_CHOICES.t_45,
            "abstract": "New abstract",
            "abstract_short": "New short abstract",
            "abstract_extra": "New extra abstract",
            "level": TALK_LEVEL.intermediate,
            "domain_level": TALK_LEVEL.advanced,
            "title": "New title",
            "sub_title": "New sub title",
            "tags": "Some, tags",
        },
    )

    # We do not advance and talk should be unchanged in DB
    assert response.status_code == 200

    # Make sure that nothing changed.
    orig_talk_dict = dump_relevant_talk_information_to_dict(talk)
    talk.refresh_from_db()
    new_talk_dict = dump_relevant_talk_information_to_dict(talk)

    assert orig_talk_dict == new_talk_dict


def test_update_speaker_updated_speaker(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()

    edit_url = reverse("cfp:update_speakers", args=[talk.uuid])
    speaker_data = dict(
        users_given_name="new",
        users_family_name="name",
        is_minor=True,
        job_title="goat",
        phone="+48123456789",
        company="widgets inc",
        company_homepage="www.widgets.inc",
        bio="this is my bio",
        i_accept_speaker_release=True,
    )

    response = user_client.post(edit_url, speaker_data)

    assert response.status_code == 302
    assert redirects_to(response, reverse("cfp:preview", args=[talk.slug]))

    user = user_client.user
    user.refresh_from_db()
    attendee_profile = user.attendeeprofile
    attendee_profile.refresh_from_db()
    assert user.assopy_user.name() == "new name"
    assert attendee_profile.phone == speaker_data["phone"]
    assert attendee_profile.is_minor == speaker_data["is_minor"]
    assert attendee_profile.job_title == speaker_data["job_title"]
    assert attendee_profile.company == speaker_data["company"]
    assert speaker_data["company_homepage"] in attendee_profile.company_homepage
    assert attendee_profile.getBio().body == speaker_data["bio"]


def test_update_speaker_updated_speaker_name(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()

    user = user_client.user
    user.first_name = "John"
    user.last_name = "Doe"
    user.save()

    edit_url = reverse("cfp:update_speakers", args=[talk.uuid])
    speaker_data = dict(
        users_given_name="New",
        users_family_name="Name",
        phone="+48123456789",
        bio="this is my bio",
        i_accept_speaker_release=True,
    )

    response = user_client.post(edit_url, speaker_data)

    assert response.status_code == 302
    assert redirects_to(response, reverse("cfp:preview", args=[talk.slug]))

    user.refresh_from_db()
    attendee_profile = user.attendeeprofile
    attendee_profile.refresh_from_db()
    assert user.assopy_user.name() == 'New Name'
    assert user.assopy_user.user.first_name == 'New'
    assert user.assopy_user.user.last_name == 'Name'


# Mark with django db only because AddSpeakerToTalkForm is a ModelForm
@mark.parametrize(
    "valid_phone", ["+48123456789", "+44 7 123 456 789", "+1 858 712 8966"]
)
def test_speaker_form_accepts_valid_international_mobile_numbers(valid_phone):
    form = AddSpeakerToTalkForm(
        {
            "users_given_name": "Joe",
            "users_family_name": "Doe",
            "phone": valid_phone,
            "bio": "ASdf bio",
            "i_accept_speaker_release": True,
        }
    )
    assert form.is_valid()


# Mark with django db only because AddSpeakerToTalkForm is a ModelForm
@mark.parametrize(
    "invalid_phone",
    ["SOME RANODM TEXT", "+4471343956789", "+4412445367"],
)
def test_speaker_form_doesnt_accept_invalid_international_mobile_numbers(
    invalid_phone
):
    form = AddSpeakerToTalkForm(
        {
            "users_given_name": "Joe",
            "users_family_name": "Doe",
            "phone": invalid_phone,
            "bio": "ASdf bio",
            "i_accept_speaker_release": True
        }
    )
    assert not form.is_valid()
    assert (
        form.errors["phone"]
        == ["Enter a valid phone number (e.g. +12125552368)."]
    )


def create_conference_with_open_cfp():
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now().date() - timedelta(days=2),
        cfp_end=timezone.now().date() + timedelta(days=1),
    )
