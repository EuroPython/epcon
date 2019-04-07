from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views

from conference.models import Speaker, TalkSpeaker, Conference
from assopy.models import Order


@login_required
def user_dashboard(request):
    proposals = get_proposals_for_current_conference(request.user)
    orders = get_orders_for_current_conference(request.user)

    return TemplateResponse(request, "ep19/bs/user_panel/dashboard.html", {
        'proposals': proposals,
        'orders': orders,
    })


def get_proposals_for_current_conference(user):
    """
    This goes through TalkSpeaker module, not Talk.created_by to correctly show
    cases if people are assigned (as co-speakers) to proposals/talks created by
    other people
    """

    try:
        speaker = user.speaker
    except Speaker.DoesNotExist:
        return None

    talkspeakers = TalkSpeaker.objects.filter(
        speaker=speaker,
        talk__conference=Conference.objects.current().code,
    )

    return [ts.talk for ts in talkspeakers]


def get_orders_for_current_conference(user):
    # HACK(artcz) -- because Order doesn't have a link to Conference, we'll
    # just filter by current's conference year
    year = Conference.objects.current().conference_start.year
    return Order.objects.filter(created__year=year, user=user.assopy_user)


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
            "post_change_redirect": reverse_lazy(
                "user_panel:password_change_done"
            ),
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
