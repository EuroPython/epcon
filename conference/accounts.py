# for some reason just doing from django.contrib.auth doesn't cut it for views
from django.contrib.auth import (
    forms as auth_forms,
    views as auth_views,
    authenticate,
)
from django.conf.urls import url
from django import forms


LOGIN_TEMPLATE = "ep19/bs/accounts/login.html"

PRIVACY_POLICY_CHECKBOX = (
    "I consent to the use of my data subject to the "
    "<a href='/privacy/'>EuroPython data privacy policy</a>"
)

PRIVACY_POLICY_ERROR = (
    "You need to consent to use of your data before we can continue"
)


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


urlpatterns = [
    url(
        r"^login/$",
        auth_views.LoginView.as_view(
            authentication_form=LoginForm, template_name=LOGIN_TEMPLATE
        ),
        name="login",
    )
]
