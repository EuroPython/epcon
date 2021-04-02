from pytest import mark

from django.urls import reverse

from email_template.models import Email

from assopy.models import AssopyUser
from conference.accounts import PRIVACY_POLICY_CHECKBOX, PRIVACY_POLICY_ERROR
from conference.models import CaptchaQuestion
from conference.users import RANDOM_USERNAME_LENGTH

from tests.common_tools import make_user, redirects_to, template_used, create_homepage_in_cms


SIGNUP_SUCCESFUL_302 = 302
SIGNUP_FAILED_200 = 200

login_url = reverse("accounts:login")


def check_login(client, email):
    "Small helper for tests to check if login works correctly"
    response = client.post(
        login_url,
        {
            "email": email,
            "password": "password",
            "i_accept_privacy_policy": True,
        },
    )
    # redirect means successful login, 200 means errors on form
    LOGIN_SUCCESFUL_302 = 302
    assert response.status_code == LOGIN_SUCCESFUL_302
    return True


def activate_only_user():
    user = AssopyUser.objects.get()
    user.user.is_active = True
    user.user.save()


@mark.django_db
def test_user_registration(client):
    """
    Tests if users can create new account on the website
    (to buy tickets, etc).
    """
    # required for redirects to /
    create_homepage_in_cms()

    # 1. test if user can create new account
    sign_up_url = reverse("accounts:signup_step_1_create_account")
    response = client.get(sign_up_url)
    assert response.status_code == 200

    assert template_used(response, "conference/accounts/signup.html")
    assert template_used(response, "conference/accounts/_login_with_google.html")
    assert template_used(response, "conference/base.html")
    assert PRIVACY_POLICY_CHECKBOX in response.content.decode("utf-8")

    assert AssopyUser.objects.all().count() == 0

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "joedoe@example.com",
            "password1": "password",
            "password2": "password",
        },
        follow=True,
    )

    assert response.status_code == SIGNUP_FAILED_200
    assert "/privacy/" in PRIVACY_POLICY_CHECKBOX
    assert "I consent to the use of my data" in PRIVACY_POLICY_CHECKBOX
    assert response.context["form"].errors["__all__"] == [PRIVACY_POLICY_ERROR]

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "joedoe@example.com",
            "password1": "password",
            "password2": "password",
            "i_accept_privacy_policy": True,
        },
        follow=True,
    )

    # check if redirect was correct
    assert template_used(
        response, "conference/accounts/signup_please_verify_email.html"
    )
    assert template_used(response, "conference/base.html")

    user = AssopyUser.objects.get()
    assert user.name() == "Joe Doe"

    assert user.user.is_active is False
    # check if the random username was generated
    assert len(user.user.username) == RANDOM_USERNAME_LENGTH

    is_logged_in = client.login(
        email="joedoe@example.com", password="password"
    )
    assert is_logged_in is False  # user is inactive

    response = client.get("/")
    assert template_used(response, "conference/homepage/home_template.html")
    assert "Joe Doe" not in response.content.decode("utf-8")
    assert "Log out" not in response.content.decode("utf-8")

    # enable the user
    user.user.is_active = True
    user.user.save()

    is_logged_in = client.login(
        email="joedoe@example.com", password="password"
    )
    assert is_logged_in

    response = client.get("/")
    assert template_used(response, "conference/homepage/home_template.html")
    # checking if user is logged in.
    assert "Joe Doe" in response.content.decode("utf-8")


@mark.django_db
def test_393_emails_are_lowercased_and_login_is_case_insensitive(client):
    """
    https://github.com/EuroPython/epcon/issues/393

    Test if we can regiester new account if we use the same email with
    different case.
    """

    sign_up_url = reverse("accounts:signup_step_1_create_account")

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "JoeDoe@example.com",
            "password1": "password",
            "password2": "password",
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == SIGNUP_SUCCESFUL_302

    user = AssopyUser.objects.get()
    assert user.name() == "Joe Doe"
    assert user.user.email == "joedoe@example.com"

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "jOEdOE@example.com",
            "password1": "password",
            "password2": "password",
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == SIGNUP_FAILED_200
    assert response.context["form"].errors["email"] == ["Email already in use"]

    user = AssopyUser.objects.get()  # still only one user
    assert user.name() == "Joe Doe"
    assert user.user.email == "joedoe@example.com"

    # activate user so we can log in
    user.user.is_active = True
    user.user.save()

    # check if we can login with lowercase
    # the emails will be lowercased in db, but user is still able to log in
    # using whatever case they want
    assert check_login(client, email="JoeDoe@example.com")
    assert check_login(client, email="joedoe@example.com")
    assert check_login(client, email="JoeDoe@example.com")
    assert check_login(client, email="JOEDOE@example.com")


@mark.django_db
def test_703_test_captcha_questions(client):
    """
    https://github.com/EuroPython/epcon/issues/703
    """

    QUESTION = "Can you foo in Python?"
    ANSWER = "Yes you can"
    CaptchaQuestion.objects.create(question=QUESTION, answer=ANSWER)
    Email.objects.create(code="verify-account")

    sign_up_url = reverse("accounts:signup_step_1_create_account")

    response = client.get(sign_up_url)
    # we have question in captcha_question.initial and captcha_answer.label
    assert "captcha_question" in response.content.decode("utf-8")
    assert "captcha_answer" in response.content.decode("utf-8")
    assert response.content.decode("utf-8").count(QUESTION) == 2

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "JoeDoe@example.com",
            "password1": "password",
            "password2": "password",
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == SIGNUP_FAILED_200  # because missing captcha

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "JoeDoe@example.com",
            "password1": "password",
            "password2": "password",
            "captcha_question": QUESTION,
            "captcha_answer": "No you can't",
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == SIGNUP_FAILED_200  # because wrong answer
    wrong_answer = ["Sorry, that's a wrong answer"]
    assert response.context["form"].errors["captcha_answer"] == wrong_answer

    response = client.post(
        sign_up_url,
        {
            "first_name": "Joe",
            "last_name": "Doe",
            "email": "JoeDoe@example.com",
            "password1": "password",
            "password2": "password",
            "captcha_question": QUESTION,
            "captcha_answer": ANSWER,
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == SIGNUP_SUCCESFUL_302
    activate_only_user()
    assert check_login(client, email="joedoe@example.com")

    # if there are no enabled questions they don't appear on the form
    CaptchaQuestion.objects.update(enabled=False)
    response = client.get(sign_up_url)
    assert "captcha_question" not in response.content.decode("utf-8")
    assert "captcha_answer" not in response.content.decode("utf-8")
    assert response.content.decode("utf-8").count(QUESTION) == 0


@mark.django_db
def test_872_login_redirects_to_user_dashboard(client):
    u = make_user(email='joe@example.com', password='foobar')
    response = client.post(
        login_url,
        {
            "email": u.email,
            "password": 'foobar',
            "i_accept_privacy_policy": True,
        },
    )
    assert response.status_code == 302
    assert redirects_to(response, "/user-panel/")
