# coding: utf-8

from datetime import timedelta
from httplib import (
    OK as HTTP_OK_200,
    NOT_FOUND as HTTP_NOT_FOUND_404,
    FOUND as HTTP_REDIRECT_302
)

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core import mail
from django.conf import settings
from django.utils import timezone

from django_factory_boy import auth as auth_factories

from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.models import Conference, Talk, Speaker


# TODO(artcz) add tests for CMS-based CFP page that redirects to the submission
# page tested below


# Using django's TestCase because of assertRedirects
# however we still run it using pytest
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
        self.user = auth_factories.UserFactory(email='joedoe@example.com',
                                               is_active=True)
        AssopyUserFactory(user=self.user)

        self.form_url = reverse("conference-paper-submission")

    def test_login_required(self):
        login_url = reverse('login') + '?next=' + self.form_url
        response = self.client.get(self.form_url)
        assert response.status_code == HTTP_REDIRECT_302
        self.assertRedirects(response, login_url)

    def test_accessing_cfp_form_before_CFP_is_opened(self):
        self.conference.cfp_start = timezone.now() + timedelta(days=2)
        self.conference.save()
        self.client.login(email='joedoe@example.com', password='password123')

        # TODO(artcz) - this test is correct but I'd expect a different
        # behaviour than 404 here. Something like a template saying "Sorry CFP
        # is not yet opened"
        response = self.client.get(self.form_url, follow=True)
        assert response.status_code == HTTP_NOT_FOUND_404

    def test_accessing_cfp_form_after_CFP_is_closed(self):
        self.conference.cfp_end = timezone.now() - timedelta(days=1)
        self.conference.save()
        self.client.login(email='joedoe@example.com', password='password123')

        # TODO(artcz) - this test is correct but I'd expect a different
        # behaviour than 404 here. Something like a template saying "Sorry CFP
        # is closed"
        response = self.client.get(self.form_url, follow=True)
        assert response.status_code == HTTP_NOT_FOUND_404

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
        VALIDATION_SUCCESSFUL_303 = 303

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
        response = self.client.post(self.form_url, talk_proposal)
        assert response.status_code == VALIDATION_SUCCESSFUL_303
        self.assertRedirects(response, profile_url,
                             status_code=303, fetch_redirect_response=False)
        talk_url = Talk.objects.get().get_absolute_url()
        assert talk_url == "/conference/talks/testing-epcon-cfp"

        # At last check if the talk is visible in the list of submitted talks
        response = self.client.get(profile_url, follow=True)
        assert response.status_code == HTTP_OK_200
        self.assertTemplateUsed(response, 'conference/profile.html')
        self.assertContains(response, talk_proposal['title'])
        self.assertContains(response, talk_url)

        # Now that a talk is already propesed, second proposal will look
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
        assert response.status_code == VALIDATION_SUCCESSFUL_303
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
