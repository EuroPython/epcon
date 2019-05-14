from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Prefetch, Case, When, Value, BooleanField
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, VotoTalk, TALK_STATUS


@login_required
def talk_voting(request):
    current_conference = Conference.objects.current()

    if not current_conference.voting():
        return TemplateResponse(request, "ep19/bs/talk_voting/voting_is_closed.html")

    if not is_user_allowed_to_vote(request.user):
        return TemplateResponse(
            request,
            "ep19/bs/talk_voting/voting_is_unavailable.html",
            {"conference": current_conference},
        )

    filter = request.GET.get("filter")
    if filter == "voted":
        extra_filters = [
            ~Q(created_by=request.user),
            ~Q(speakers__user__in=[request.user]),
            Q(id__in=VotoTalk.objects.filter(user=request.user).values("talk_id")),
        ]
    elif filter == "not-voted":
        extra_filters = [
            ~Q(created_by=request.user),
            ~Q(speakers__user__in=[request.user]),
            ~Q(id__in=VotoTalk.objects.filter(user=request.user).values("talk_id")),
        ]
    elif filter == "mine":
        extra_filters = [Q(created_by=request.user) | Q(speakers__user__in=[request.user])]
    else:
        filter = "all"
        extra_filters = []

    talks = (
        Talk.objects.filter(
            Q(conference=current_conference.code)
            & Q(admin_type="")
            & Q(status=TALK_STATUS.proposed)
        )
        .filter(*extra_filters)
        .order_by("?")
        .prefetch_related(
            Prefetch(
                "vototalk_set",
                queryset=VotoTalk.objects.filter(user=request.user),
                to_attr="votes",
            )
        )
        .annotate(
            can_vote=Case(
                When(created_by=request.user, then=Value(False)),
                When(speakers__user__in=[request.user], then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            )
        )
    )

    return TemplateResponse(
        request,
        "ep19/bs/talk_voting/voting.html",
        {"talks": talks, "VotingOptions": VotingOptions, "filter": filter},
    )


def is_user_allowed_to_vote(user):
    """
    Checks if user is allowed to vote at the moment of accessing this function
    This usually means checking if they have at least one ticket associated
    with their account (either for this or any of the past years
    """
    is_allowed = (
        user.ticket_set.all().exists()
        or Talk.objects.proposed()
        .filter(created_by=user, conference=Conference.objects.current().code)
        .exists()
    )
    return is_allowed


@login_required
def vote_on_a_talk(request, talk_uuid):
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    # Users can't vote on their own talks.
    if (
        talk.created_by == request.user
        or talk.speakers.filter(pk=request.user.pk).exists()
    ):
        return TemplateResponse(
            request,
            "ep19/bs/talk_voting/_voting_form.html",
            {"talk": talk, "db_vote": None, "VotingOptions": VotingOptions},
        )

    try:
        db_vote = VotoTalk.objects.get(user=request.user, talk=talk)
    except VotoTalk.DoesNotExist:
        db_vote = None

    if request.method == "POST":
        vote = int(request.POST.get("vote"))
        assert vote in VotingOptions.ALL

        try:
            db_vote = VotoTalk.objects.get(user=request.user, talk=talk)

        except VotoTalk.DoesNotExist:

            if vote == VotingOptions.no_vote:
                return TemplateResponse(
                    request,
                    "ep19/bs/talk_voting/_voting_form.html",
                    {"talk": talk, "db_vote": None, "VotingOptions": VotingOptions},
                )

            db_vote = VotoTalk.objects.create(user=request.user, talk=talk, vote=vote)

        if vote == VotingOptions.no_vote:
            db_vote.delete()
            return TemplateResponse(
                request,
                "ep19/bs/talk_voting/_voting_form.html",
                {"talk": talk, "db_vote": None, "VotingOptions": VotingOptions},
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
    url(r"^$", talk_voting, name="talks"),
    url(r"^vote-on/(?P<talk_uuid>[\w]+)/$", vote_on_a_talk, name="vote"),
]
