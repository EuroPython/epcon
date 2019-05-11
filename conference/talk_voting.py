from django.conf.urls import url
from django.db.models import Q

from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required

from conference.models import Conference, Talk


@login_required
def talk_voting(request):

    # TODO: check if voting is open
    current_conference = Conference.objects.current()
    talks = Talk.objects.filter(
        Q(conference=current_conference.code) & ~Q(created_by=request.user)
    ).order_by("?")

    return TemplateResponse(
        request, "ep19/bs/talk_voting/voting.html", {"talks": talks}
    )


def vote_on_a_talk(request, talk_uuid):

    if request.method == "POST":
        ...

    return HttpResponse(f"Vote on {talk_uuid}")


urlpatterns = [url("^$", talk_voting)]
