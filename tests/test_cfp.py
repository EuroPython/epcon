# coding: utf-8

from datetime import timedelta
from http.client import (
    OK as HTTP_OK_200,
    # NOT_FOUND as HTTP_NOT_FOUND_404,
    FOUND as HTTP_REDIRECT_302
)

import pytest
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core import mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

from django_factory_boy import auth as auth_factories

from tests.factories import AssopyUserFactory
from conference.models import (
    Conference,
    Talk,
    Speaker,
    ConferenceTag,
    TALK_LEVEL
)
from taggit.models import Tag


# TODO(artcz) add tests for CMS-based CFP page that redirects to the submission
# page tested below


# Using django's TestCase because of assertRedirects
# however we still run it using pytest
@pytest.mark.skip(
    "There's a new implementation of cfp, and this one no longer needs to be"
    " fully supported. Left as documentation. "
    "To be removed after it's reviewed in #966"
)
class TestCFP(TestCase):
    """
    Test everything related to CFP
    """

    def setUp(self):
        self.conference = Conference.objects.create(
            code=settings.CONFERENCE_CONFERENCE,
            name=settings.CONFERENCE_CONFERENCE,
            # by default start with open CFP
            cfp_start=timezone.now() - timedelta(days=2),
            cfp_end=timezone.now()   + timedelta(days=2)
        )

        # default password is 'password123' per django_factory_boy
        admin = User.objects.create_superuser(
            'admin', 'admin@example.com', 'admin')
        AssopyUserFactory(user=admin)

        self.user = auth_factories.UserFactory(
            email='joedoe@example.com', is_active=True)
        AssopyUserFactory(user=self.user)

        self.form_url = reverse("conference-paper-submission")

    def test_login_required(self):
        login_url = reverse('accounts:login') + '?next=' + self.form_url
        response = self.client.get(self.form_url)
        assert response.status_code == HTTP_REDIRECT_302
        self.assertRedirects(response, login_url)

    def test_accessing_cfp_form_before_CFP_is_opened(self):
        self.conference.cfp_start = timezone.now() + timedelta(days=2)
        self.conference.save()
        self.client.login(email='joedoe@example.com', password='password123')

        response = self.client.get(self.form_url, follow=True)
        assert response.status_code == HTTP_OK_200
        self.assertTemplateUsed(response,
                                "conference/cfp/cfp_not_started.html")

    def test_accessing_cfp_form_after_CFP_is_closed(self):
        self.conference.cfp_end = timezone.now() - timedelta(days=1)
        self.conference.save()
        self.client.login(email='joedoe@example.com', password='password123')

        response = self.client.get(self.form_url, follow=True)
        assert response.status_code == HTTP_OK_200
        self.assertTemplateUsed(response,
                                "conference/cfp/cfp_already_closed.html")

    def test_accessing_cfp_form_while_cfp_is_live(self):
        self.client.login(email='joedoe@example.com', password='password123')

        response = self.client.get(self.form_url, follow=True)
        assert response.status_code == HTTP_OK_200
        self.assertTemplateUsed(response, "conference/paper_submission.html")

    def test_post_some_proposals(self):
        assert Talk.objects.all().count() == 0
        self.client.login(email='joedoe@example.com', password='password123')

        assert Speaker.objects.count() == 0
        with self.assertRaises(Speaker.DoesNotExist):
            self.user.speaker

        VALIDATION_FAILED_200     = HTTP_OK_200
        VALIDATION_SUCCESSFUL_302 = 302

        required_proposal_fields = [
            'title', 'abstract', 'abstract_short', 'level', 'tags',
            'slides_agreement', 'video_agreement', 'type',
        ]

        required_speaker_fields = [
            'bio', 'first_name', 'last_name', 'phone',
            'birthday', 'personal_agreement',
        ]

        required_fields_for_first_proposal =\
            required_speaker_fields + required_proposal_fields
        required_fields_for_next_proposal = required_proposal_fields

        def required_fields_not_filled(response, fields):
            """
            Helper function
            """
            errors = response.context['form'].errors

            for f in fields:
                assert errors[f] == ['This field is required.']
                del errors[f]

            # we make sure there are no other errors in the form
            assert errors == {}

        empty_submission = {}
        response = self.client.post(self.form_url, empty_submission)
        assert response.status_code == VALIDATION_FAILED_200
        required_fields_not_filled(response,
                                   required_fields_for_first_proposal)

        dummy_data_in_all_required_fields = {
            f: "foo"
            for f in required_fields_for_first_proposal
        }
        response = self.client.post(self.form_url,
                                    dummy_data_in_all_required_fields)
        assert response.status_code == VALIDATION_FAILED_200

        # birthday, type and level require specific data
        assert {'birthday', 'type', 'level'} ==\
            set(response.context['form'].errors.keys())

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "phone": "41331237",
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        profile_url = reverse("conference-myself-profile")
        thank_you_url = reverse('cfp-thank-you-for-proposal')
        response = self.client.post(self.form_url, talk_proposal)
        self.assertRedirects(response, thank_you_url,
                             status_code=VALIDATION_SUCCESSFUL_302,
                             fetch_redirect_response=False)
        talk_url = Talk.objects.get().get_absolute_url()
        assert talk_url == "/conference/talks/testing-epcon-cfp"

        # At last check if the talk is visible in the list of submitted talks
        response = self.client.get(profile_url, follow=True)
        assert response.status_code == HTTP_OK_200
        self.assertTemplateUsed(response, 'conference/profile.html')
        self.assertContains(response, talk_proposal['title'])
        self.assertContains(response, talk_url)

        # Now that a talk is already proposed, second proposal will look
        # slightly different
        assert Speaker.objects.get()
        response = self.client.get(self.form_url)
        self.assertContains(response, "You have already submitted 1 proposal")

        response = self.client.post(self.form_url, empty_submission)
        required_fields_not_filled(response, required_fields_for_next_proposal)

        talk_proposal = {
            "type": "t_45",
            "title": "More about EPCON testing",
            "abstract_short": "Longer talk about testing",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "tags": "django, testing, slides",
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302
        assert Talk.objects.all().count() == 2

        # check the form again
        response = self.client.get(self.form_url)
        self.assertContains(response, "You have already submitted 2 proposals")

        # NOTE(artcz)(2018-02-27)
        # This assertion checks if we're not sending emails during the
        # submission process.
        # There is a signal that is triggered when new Talk is created
        # (_new_paper_email) and it sends emails to people on the
        # CONFERENCE_TALK_SUBMISSION_NOTIFICATION_EMAIL list.
        # For now this list is empty, so it shouldn't send any emails. If we
        # ever change that (either by removing the signal or putting some
        # emails on that list) – we should update this test
        assert len(mail.outbox) == 0

    def test_ignores_new_tags(self):
        assert Talk.objects.all().count() == 0
        assert ConferenceTag.objects.count() == 0
        assert Tag.objects.count() == 0
        self.client.login(email='joedoe@example.com', password='password123')

        VALIDATION_SUCCESSFUL_302 = 302

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "phone": "41331237",
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        assert ConferenceTag.objects.count() == 0
        assert Tag.objects.count() == 0
        talk = Talk.objects.first()

        assert talk.tags.count() == 0

        assert Speaker.objects.get()

        # second proposal

        talk_proposal = {
            "type": "t_45",
            "title": "More about EPCON testing",
            "abstract_short": "Longer talk about testing",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "tags": "django, testing, slides",
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        assert ConferenceTag.objects.count() == 0
        assert Tag.objects.count() == 0

    def test_ignores_new_tags_keeping_predefined_ones(self):
        ConferenceTag.objects.create(name='django')
        ConferenceTag.objects.create(name='love')

        assert Talk.objects.all().count() == 0
        assert ConferenceTag.objects.count() == 2
        assert Tag.objects.count() == 0
        self.client.login(email='joedoe@example.com', password='password123')

        VALIDATION_SUCCESSFUL_302 = 302

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "phone": "41331237",
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        assert ConferenceTag.objects.count() == 2
        talk = Talk.objects.last()

        assert talk.tags.count() == 1

        assert 'django' in talk.tags.all().values_list('name', flat=True)

        # second proposal

        talk_proposal = {
            "type": "t_45",
            "title": "More about EPCON testing",
            "abstract_short": "Longer talk about testing",
            "abstract": "Using django TestCase and pytest",
            "level": "advanced",
            "tags": "love, testing, slides",
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        assert ConferenceTag.objects.count() == 2

        talk = Talk.objects.first()

        assert talk.tags.count() == 1

        assert talk.title == 'More about EPCON testing'
        assert 'love' in talk.tags.all().values_list('name', flat=True)

    def test_allows_very_long_description(self):
        assert Tag.objects.count() == 0
        self.client.login(email='joedoe@example.com', password='password123')

        VALIDATION_SUCCESSFUL_302 = 302

        abstract = 'a' * 5000

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": abstract,
            "level": "advanced",
            "phone": "41331237",
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()

        assert talk.abstracts.all()[0].body == abstract

        # second proposal

        talk_proposal = {
            "type": "t_45",
            "title": "More about EPCON testing",
            "abstract_short": "Longer talk about testing",
            "abstract": abstract,
            "level": "advanced",
            "tags": "love, testing, slides",
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()

        assert talk.abstracts.all()[0].body == abstract

    def test_allows_talk_domain_and_domain_level(self):
        assert Tag.objects.count() == 0
        self.client.login(email='joedoe@example.com', password='password123')

        VALIDATION_SUCCESSFUL_302 = 302
        abstract = 'aaaaaaaaaaaa'

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": abstract,
            "level": TALK_LEVEL.advanced,
            "phone": "41331237",
            "domain": "django",
            "domain_level": TALK_LEVEL.intermediate,
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()
        # Checking issue #654 – if talk is accessible after submission
        response = self.client.get(talk.get_absolute_url())
        self.assertTemplateUsed(response, "conference/talk.html")

        assert talk.domain == 'django'
        assert talk.domain_level == TALK_LEVEL.intermediate
        assert talk.level == TALK_LEVEL.advanced

        # second proposal

        talk_proposal = {
            "type": "t_45",
            "title": "More about EPCON testing",
            "abstract_short": "Longer talk about testing",
            "abstract": abstract,
            "level": TALK_LEVEL.intermediate,
            "tags": "love, testing, slides",
            "domain": "devops",
            "domain_level": TALK_LEVEL.advanced,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()
        # Checking issue #654 – if talk is accessible after submission
        response = self.client.get(talk.get_absolute_url())
        self.assertTemplateUsed(response, "conference/talk.html")

        assert talk.abstracts.all()[0].body == abstract
        assert talk.domain == 'devops'
        assert talk.domain_level == TALK_LEVEL.advanced
        assert talk.level == TALK_LEVEL.intermediate

    def test_662_editing_cfp_proposal(self):
        """
        https://github.com/EuroPython/epcon/issues/662
        """

        self.client.login(email=self.user.email, password='password123')
        VALIDATION_SUCCESSFUL_302 = 302
        EDIT_SUCCESSFUL_303 = 303
        abstract = 'aaaaaaaaaaaa'

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": abstract,
            "level": TALK_LEVEL.advanced,
            "phone": "41331237",
            "domain": "django",
            "domain_level": TALK_LEVEL.intermediate,
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()
        assert talk.abstract_short == "Short talk about testing CFP"
        self.assertTemplateUsed(
            self.client.get(talk.get_absolute_url()),
            "conference/talk.html"
        )

        talk_proposal["abstract_short"] = "First edit"
        response = self.client.post(talk.get_absolute_url(), talk_proposal)
        assert response.status_code == EDIT_SUCCESSFUL_303

        talk = Talk.objects.first()
        assert talk.abstract_short == "First edit"

        talk_proposal["abstract_short"] = "Second edit"
        response = self.client.post(talk.get_absolute_url(), talk_proposal)
        assert response.status_code == EDIT_SUCCESSFUL_303

        talk = Talk.objects.first()
        assert talk.abstract_short == "Second edit"

    def test_665_edit_with_other_in_django_admin(self):
        """
        https://github.com/EuroPython/epcon/issues/665
        """
        self.client.login(email=self.user.email, password='password123')
        VALIDATION_SUCCESSFUL_302 = 302
        EDIT_SUCCESSFUL_302       = 302
        abstract = 'aaaaaaaaaaaa'

        talk_proposal = {
            "type": "t_30",
            'first_name': 'Joe',
            'last_name': 'Doe',
            "birthday": "2018-02-26",
            'bio': "Python developer",
            "title": "Testing EPCON CFP",
            "abstract_short": "Short talk about testing CFP",
            "abstract": abstract,
            "level": TALK_LEVEL.advanced,
            "phone": "41331237",
            "domain": settings.CONFERENCE_TALK_DOMAIN.django,
            "domain_level": TALK_LEVEL.intermediate,
            "tags": "django, testing, slides",
            "personal_agreement": True,
            "slides_agreement": True,
            "video_agreement": True,
        }

        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_302

        talk = Talk.objects.first()

        # relogin as staff user
        self.client.login(email='admin@example.com', password='admin')
        response = self.client.get(talk.get_admin_url())
        self.assertTemplateUsed(response, "admin/change_form.html")

        # TODO: this should be probably dynamically generated from the GET
        # response above, but not sure how to correctly dump formset to dict,
        # so instead I just served it's response and did parse_qsl on the
        # whole POST.
        admin_talk_edit = {
            '_save': 'Save',
            'abstract_short': 'Short talk about testing CFP',
            'abstracts_en': 'aaaaaaaaaaaa',
            'conference': 'ep2018',
            'domain': settings.CONFERENCE_TALK_DOMAIN.other,
            'domain_level': 'intermediate',
            'duration': '30',
            'language': 'en',
            'level': 'advanced',
            'slug': 'testing-epcon-cfp',
            'status': 'proposed',
            'tags': "django, testing, slides",
            'talkspeaker_set-0-id': '1',
            'talkspeaker_set-0-speaker': '2',
            'talkspeaker_set-0-talk': '1',
            'talkspeaker_set-1-talk': '1',
            'talkspeaker_set-INITIAL_FORMS': '1',
            'talkspeaker_set-MAX_NUM_FORMS': '1000',
            'talkspeaker_set-MIN_NUM_FORMS': '0',
            'talkspeaker_set-TOTAL_FORMS': '2',
            'talkspeaker_set-__prefix__-talk': '1',
            'title': 'Testing EPCON CFP',
            'type': 't_30'
        }

        assert settings.CONFERENCE_TALK_DOMAIN.other == ''
        response = self.client.post(talk.get_admin_url(), admin_talk_edit)
        assert response.status_code == EDIT_SUCCESSFUL_302

        talk = Talk.objects.first()
        assert talk.domain != settings.CONFERENCE_TALK_DOMAIN.django
        assert talk.domain == settings.CONFERENCE_TALK_DOMAIN.other
        assert talk.domain == ''
