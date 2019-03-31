from datetime import timedelta

from pytest import mark
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone

from conference.models import Conference, Talk, TALK_TYPE_CHOICES, TALK_LEVEL
from conference.tests.factories.talk import TalkFactory
from conference.cfp import dump_relevant_talk_information_to_dict

from tests.common_tools import redirects_to, template_used


@mark.django_db
@mark.parametrize(
    "url",
    [
        reverse("cfp:step1_submit_proposal"),
        # using some random uuid because we just need to resolve url
        reverse("cfp:step2_add_speakers", args=["ABCDEFI"]),
        reverse("cfp:step3_thanks", args=["ABCDEFI"]),
    ],
)
def test_if_cfp_pages_are_login_required(client, url):
    response = client.get(url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


@mark.django_db
def test_if_cfp_pages_are_unavailable_if_cfp_is_undefined(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cfp/cfp_is_closed.html")


@mark.django_db
def test_if_cfp_pages_are_unavailable_if_cfp_is_in_the_future(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() + timedelta(days=2),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cfp/cfp_is_closed.html")


@mark.django_db
def test_if_cfp_pages_are_unavailable_if_cfp_is_in_the_past(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() - timedelta(days=2),
        cfp_end=timezone.now() - timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cfp/cfp_is_closed.html")


@mark.django_db
def test_if_cfp_pages_are_available_if_cfp_is_active(user_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() - timedelta(days=2),
        cfp_end=timezone.now() + timedelta(days=1),
    )
    step1_url = reverse("cfp:step1_submit_proposal")

    response = user_client.get(step1_url)
    assert response.status_code == 200
    assert template_used(response, "ep19/bs/cfp/step1_talk_info.html")


@mark.django_db
def test_if_user_can_submit_talk_details_and_is_redirect_to_step2(user_client):
    STEP1_CORRECT_REDIRECT_302 = 302

    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() - timedelta(days=2),
        cfp_end=timezone.now() + timedelta(days=1),
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

    assert redirects_to(
        response, reverse("cfp:step2_add_speakers", args=[talk.uuid])
    )


@mark.django_db
def test_if_user_can_add_a_speaker_to_a_proposal(user_client):
    create_conference_with_open_cfp()
    # STEP2_CORRECT_REDIRECT_302 = 302

    talk = TalkFactory()
    talk.setAbstract(
        "Setting abstract just because we'll need it to dump later"
    )
    step2_url = reverse("cfp:step2_add_speakers", args=[talk.uuid])

    response = user_client.get(step2_url)
    assert template_used(response, "ep19/bs/cfp/step2_add_speaker.html")

    response = user_client.post(
        step2_url,
        {
            "users_given_name": "Joe Doe",
            "phone": "+4812345678",
            "birthday": "2010-02-03",
            "bio": "ASdf bio",
        },
    )

    talk.refresh_from_db()
    talk_dict = dump_relevant_talk_information_to_dict(talk)
    speaker = talk_dict["speakers"][0]
    assert speaker["name"] == "Joe Doe"
    assert speaker["company"] == ""
    assert speaker["company_homepage"] == ""
    assert speaker["bio"] == "ASdf bio"
    assert speaker["phone"] == "+4812345678"

    assert redirects_to(
        response, reverse("cfp:step3_thanks", args=[talk.uuid])
    )


@mark.django_db
def test_if_correct_thanks_page_is_rendered(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    step3_url = reverse("cfp:step3_thanks", args=[talk.uuid])

    response = user_client.get(step3_url)
    assert template_used(response, "ep19/bs/cfp/step3_thanks.html")


@mark.django_db
def test_thanks_page_contains_link_to_preview_proposal(user_client):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    step3_url = reverse("cfp:step3_thanks", args=[talk.uuid])

    preview_link = reverse("cfp:preview", args=[talk.slug])
    response = user_client.get(step3_url)

    assert preview_link in response.content.decode()


@mark.django_db
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


@mark.django_db
def test_preview_page_contains_edit_link_if_cfp_is_open_and_user_is_author(
    user_client
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    talk.created_by = user_client.user
    talk.save()
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link in response.content.decode()


@mark.django_db
def test_preview_page_doesnt_contain_edit_link_if_cfp_is_open_but_user_is_not_author(  # NOQA
    user_client
):
    create_conference_with_open_cfp()
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link not in response.content.decode()


@mark.django_db
def test_preview_page_doesnt_contain_edit_link_if_cfp_is_closed_and_user_is_author(  # NOQA
    user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() - timedelta(days=2),
        cfp_end=timezone.now() - timedelta(days=1),
    )
    talk = TalkFactory()
    talk.setAbstract("some abstract")
    preview_url = reverse("cfp:preview", args=[talk.slug])
    edit_link = reverse("cfp:update", args=[talk.uuid])

    response = user_client.get(preview_url)

    assert edit_link not in response.content.decode()


@mark.django_db
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


@mark.django_db
def test_admin_user_can_access_program_wg_download(admin_client):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )
    url = reverse("cfp:program_wg_download_all_talks")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == {"talks": []}


def create_conference_with_open_cfp():
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        cfp_start=timezone.now() - timedelta(days=2),
        cfp_end=timezone.now() + timedelta(days=1),
    )
