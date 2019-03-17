from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views


@login_required
def user_dashboard(request):

    return TemplateResponse(request, "ep19/bs/user_panel/dashboard.html", {})


urlpatterns = [
    url(r"^$", user_dashboard, name="dashboard"),

    # Password change, using default django views.
    # TODO(artcz): Those are Removed in Django21 and we should replcethem with
    # class based PasswordChange{,Done}View
    url(
        r"^password/change/$",
        auth_views.password_change,
        kwargs={
            "template_name": "ep19/bs/user_panel/password_change.html",
            "post_change_redirect":
            reverse_lazy("user_panel:password_change_done"),
        },
        name="password_change",
    ),
    url(
        r"^password/change/done/$",
        auth_views.password_change_done,
        kwargs={
            "template_name": "ep19/bs/user_panel/password_change_done.html"
        },
        name="password_change_done",
    ),
]
