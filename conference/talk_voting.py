from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, VotoTalk


@login_required
def talk_voting(request):

    # TODO: check if voting is open
    current_conference = Conference.objects.current()
    talks = (
        Talk.objects.filter(
            Q(conference=current_conference.code) & ~Q(created_by=request.user)
        )
        .order_by("?")
        .prefetch_related(
            Prefetch(
                "vototalk_set",
                queryset=VotoTalk.objects.filter(user=request.user),
                to_attr="votes",
            )
        )
    )

    return TemplateResponse(
        request,
        "ep19/bs/talk_voting/voting.html",
        {"talks": talks, "VotingOptions": VotingOptions},
    )


@login_required
def vote_on_a_talk(request, talk_uuid):
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    try:
        db_vote = VotoTalk.objects.get(user=request.user, talk=talk)
    except VotoTalk.DoesNotExist:
        db_vote = None

    if request.method == "POST":
        print(request.POST)
        vote = int(request.POST.get("vote"))
        assert vote in VotingOptions.ALL

        try:
            db_vote = VotoTalk.objects.get(user=request.user, talk=talk)

        except VotoTalk.DoesNotExist:

            if vote == VotingOptions.no_vote:
                return TemplateResponse(
                    request,
                    "ep19/bs/talk_voting/_voting_form.html",
                    {
                        "talk": talk,
                        "db_vote": None,
                        "VotingOptions": VotingOptions,
                    },
                )

            db_vote = VotoTalk.objects.create(
                user=request.user, talk=talk, vote=vote
            )

        if vote == VotingOptions.no_vote:
            db_vote.delete()
            return TemplateResponse(
                request,
                "ep19/bs/talk_voting/_voting_form.html",
                {
                    "talk": talk,
                    "db_vote": None,
                    "VotingOptions": VotingOptions,
                },
            )

        db_vote.vote = vote
        db_vote.save()

    return TemplateResponse(
        request,
        "ep19/bs/talk_voting/_voting_form.html",
        {"talk": talk, "db_vote": db_vote, "VotingOptions": VotingOptions},
    )


class VotingOptions:
    no_vote = -1
    not_interested = 0
    maybe = 3
    want_to_see = 7
    must_see = 10

    ALL = [no_vote, not_interested, maybe, want_to_see, must_see]


urlpatterns = [
    url(r"^$", talk_voting),
    url(r"^vote-on/(?P<talk_uuid>[\w]+)/$", vote_on_a_talk, name="vote"),
]
