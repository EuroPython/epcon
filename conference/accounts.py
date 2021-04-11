import random

from django import forms
from django.conf import settings
from django.conf.urls import url as re_path
from django.contrib import messages
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import views as auth_views
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.template.response import TemplateResponse

import shortuuid

from assopy.models import AssopyUser, Token
from conference.models import CaptchaQuestion, AttendeeProfile
from p3.models import P3Profile


LOGIN_TEMPLATE = "conference/accounts/login.html"

PRIVACY_POLICY_CHECKBOX = (
    "I consent to the use of my data subject to the "
    "<a href='/privacy/'>EuroPython data privacy policy</a>"
)

PRIVACY_POLICY_ERROR = (
    "You need to consent to use of your data before we can continue"
)

EMAIL_VERIFICATION_SUBJECT = "%s: Please verify your email" % settings.CONFERENCE_NAME


class LoginForm(auth_forms.AuthenticationForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.widgets.PasswordInput)
    i_accept_privacy_policy = forms.BooleanField(label=PRIVACY_POLICY_CHECKBOX)

    field_order = ["email", "password", "i_accept_privacy_policy"]

    def __init__(self, *args, **kwargs):
        # NOTE(artcz) we also overload init to handle 'request' that's passed
        # to this form at some point
        super().__init__(*args, **kwargs)
        del self.fields["username"]

    def clean(self):
        data = self.cleaned_data
        if not data.get("i_accept_privacy_policy"):
            raise forms.ValidationError(PRIVACY_POLICY_ERROR)

        if data.get("email") and data.get("password"):
            user = authenticate(email=data["email"], password=data["password"])
            self.user_cache = user

            if user is None:
                raise forms.ValidationError("Invalid credentials")

            elif not user.is_active:
                raise forms.ValidationError("This account is inactive.")

        return data


def signup_step_1_create_account(request) -> [TemplateResponse, redirect]:
    """
    Creates new account in the system, populating both auth.User and
    assopy.AssopyUser
    """

    if request.user.is_authenticated:
        return redirect('user_panel:dashboard')

    form = NewAccountForm()
    form.order_fields([
        'first_name',  'last_name', 'email', 'password1', 'password2',
        'captcha_question', 'captcha_answer', 'i_accept_privacy_policy',
        ])

    if request.method == 'POST':
        form = NewAccountForm(data=request.POST)

        if form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                assopy_user = AssopyUser.objects.create_user(
                    email=data['email'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    password=data['password1'],
                )
                get_or_create_attendee_profile_for_new_user(assopy_user.user)
                current_site = get_current_site(request)
                send_verification_email(assopy_user.user, current_site)

                messages.success(request, "Email verification sent")

            return redirect('accounts:signup_step_2_please_verify_email')

    return TemplateResponse(request, "conference/accounts/signup.html", {
        'form': form,
        'next': request.GET.get('next', '/'),
    })


def signup_step_2_please_verify_email(request):
    return TemplateResponse(
        request, "conference/accounts/signup_please_verify_email.html", {}
    )


def send_verification_email(user, current_site) -> None:

    new_token = create_new_email_verification_token(user)
    verification_path = reverse(
        "accounts:handle_verification_token", args=[new_token.token]
    )
    full_url = f'https://{current_site.domain}{verification_path}'

    content = render_to_string("conference/emails/signup_verification_email.txt", {
        'new_token': new_token,
        'verification_email_url': full_url,
    })

    send_mail(
        subject=EMAIL_VERIFICATION_SUBJECT,
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def social_connect_profile(backend, user, response, *args, **kwargs) -> None:
    """
    This is used by python social auth to connect and/or pre-create all user
    profiles (AssopyUser, AttendeeProfile, etc.
    """

    AssopyUser.objects.get_or_create(user=user)
    get_or_create_attendee_profile_for_new_user(user=user)


def get_or_create_attendee_profile_for_new_user(user):
    try:
        attendee = AttendeeProfile.objects.get(user=user)
    except AttendeeProfile.DoesNotExist:
        attendee = AttendeeProfile(
            user=user,
            slug=slug_for_user(user),
            uuid=shortuuid.ShortUUID().random(length=7),
        )
        attendee.save()
        # needed because it creates a separate object in db.
        attendee.setBio('bio')

    if not attendee.p3_profile:
        p3_profile = P3Profile(profile=attendee)
        p3_profile.save()

    return attendee


def slug_for_user(user) -> str:
    name = f'{user.first_name} {user.last_name}'
    slug = slugify(name)

    while AttendeeProfile.objects.filter(slug=slug).exists():
        # add random 6 digit number as long as clashes occur
        noise = random.randint(1e5, 1e6)
        slug = f'{slug}-{noise}'

    return slug


def create_new_email_verification_token(user) -> Token:
    return Token.objects.create(
        token=shortuuid.uuid(),
        ctype=Token.TYPES.EMAIL_VERIFICATION,
        user=user,
        payload='',
    )


def handle_verification_token(request, token) -> [404, redirect]:
    """
    This is just a reimplementation of what was used previously with OTC

    https://github.com/EuroPython/epcon/pull/809/files
    """
    token = get_object_or_404(Token, token=token)

    logout(request)
    user = token.user
    user.is_active = True
    user.save()
    user = authenticate(uid=user.id)
    login(request, user)

    token.delete()

    messages.success(request, 'Email verfication complete')
    return redirect('user_panel:dashboard')

class CaptchaQuestionForm(forms.Form):
    # Additional captcha field with simple python questions
    # https://github.com/EuroPython/epcon/issues/703
    captcha_question = forms.CharField(widget=forms.HiddenInput)
    captcha_answer = forms.CharField()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        random_question = self.get_random_captcha_question()
        if random_question:
            self.fields['captcha_question'].initial = random_question.question
            self.fields['captcha_answer'].label     = random_question.question
        else:
            del self.fields['captcha_question']
            del self.fields['captcha_answer']

    def get_random_captcha_question(self):
        try:
            return CaptchaQuestion.objects.get_random_question()
        except CaptchaQuestion.NoQuestionsAvailable:
            return None

    def clean_captcha_answer(self):
        question = self.cleaned_data['captcha_question']
        cq = CaptchaQuestion.objects.get(question=question)
        if cq.answer.strip().lower() != self.cleaned_data['captcha_answer'].strip().lower():
            raise forms.ValidationError("Sorry, that's a wrong answer")
        return self.cleaned_data['captcha_question']


class NewAccountForm(CaptchaQuestionForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput
    )


    # Keep this in sync with LoginForm.i_accept_privacy_policy
    i_accept_privacy_policy = forms.BooleanField(
        label=PRIVACY_POLICY_CHECKBOX
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Email already in use')

        return email.lower()

    def clean(self):
        if not self.cleaned_data.get('i_accept_privacy_policy'):
            raise forms.ValidationError(PRIVACY_POLICY_ERROR)

        if not self.is_valid():
            return super().clean()

        data = self.cleaned_data
        if data['password1'] != data['password2']:
            raise forms.ValidationError('password mismatch')
        return data


urlpatterns = [
    re_path(
        r"^login/$",
        auth_views.LoginView.as_view(
            authentication_form=LoginForm, template_name=LOGIN_TEMPLATE
        ),
        name="login",
    ),
    re_path(r"^logout/$", auth_views.LogoutView.as_view(), name="logout"),
    re_path(
        r"^signup/$",
        signup_step_1_create_account,
        name="signup_step_1_create_account",
    ),
    re_path(
        r"^signup/thanks/$",
        signup_step_2_please_verify_email,
        name="signup_step_2_please_verify_email",
    ),
    re_path(
        # 22 not 36 because we use short uuid
        r"^signup/verify-email/(?P<token>\w{22})/$",
        handle_verification_token,
        name="handle_verification_token",
    ),
    # Password reset, using default django views.
    re_path(
        r"^password-reset/$",
        auth_views.PasswordResetView.as_view(
            template_name="conference/accounts/password_reset.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
            email_template_name="conference/emails/password_reset_email.txt",
            subject_template_name="conference/emails/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    re_path(
        r"^password-reset/done/$",
        auth_views.PasswordResetDoneView.as_view(
            template_name="conference/accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    re_path(
        r"^reset/(?P<uidb64>[\w-]+)/(?P<token>[\w]{1,13}-[\w]{1,20})/$",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="conference/accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    re_path(
        r"^reset/done/$",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="conference/accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
