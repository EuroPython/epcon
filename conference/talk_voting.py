import random

from django.urls import re_path
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Q, Prefetch, Case, When, Value, BooleanField
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from conference.models import Conference, Talk, VotoTalk, TALK_STATUS, TALK_TYPE_CHOICES
from conference import fares

@login_required
def talk_voting(request):
    current_conference = Conference.objects.current()

    if not current_conference.voting():
        return TemplateResponse(request, "conference/talk_voting/voting_is_closed.html")

    if not is_user_allowed_to_vote(request.user):
        return TemplateResponse(
            request,
            "conference/talk_voting/voting_is_unavailable.html",
            {"conference": current_conference},
        )

    filter = request.GET.get("filter", "all")
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
        extra_filters = [
            Q(created_by=request.user) | Q(speakers__user__in=[request.user])
        ]
    else:
        extra_filters = []

    talk_type = request.GET.get("talk_type", "all")
    if talk_type == "talk":
        extra_filters += [
            Q(
                type__in=[
                    TALK_TYPE_CHOICES.t_30,
                    TALK_TYPE_CHOICES.t_45,
                    TALK_TYPE_CHOICES.t_60,
                ]
            )
        ]
    if talk_type == "training":
        extra_filters += [Q(type__in=[TALK_TYPE_CHOICES.r_180])]
    if talk_type == "poster":
        extra_filters += [
            Q(
                type__in=[
                    TALK_TYPE_CHOICES.i_60,
                    TALK_TYPE_CHOICES.p_180,
                    TALK_TYPE_CHOICES.n_60,
                    TALK_TYPE_CHOICES.n_90,
                ]
            )
        ]
    if talk_type == "helpdesk":
        extra_filters += [Q(type__in=[TALK_TYPE_CHOICES.h_180])]

    talks = find_talks(request.user, current_conference, extra_filters)

    return TemplateResponse(
        request,
        "conference/talk_voting/voting.html",
        {
            "talks": talks,
            "VotingOptions": VotingOptions,
            "filter": filter,
            "talk_type": talk_type,
        },
    )


def find_talks(user, conference, extra_filters):
    """
    This prepares a queryset of Talks with custom data, with an option to pass
    additional filters related to which talks we want to show.
    """
    talks = (
        Talk.objects.filter(
            Q(conference=conference.code)
            & Q(admin_type="")
            & Q(status=TALK_STATUS.proposed)
            & ~Q(speakers=None)
        )
        .filter(*extra_filters)
        .prefetch_related(
            Prefetch(
                "vototalk_set",
                queryset=VotoTalk.objects.filter(user=user),
                to_attr="votes",
            )
        )
        .annotate(
            can_vote=Case(
                When(created_by=user, then=Value(False)),
                When(speakers__user__username__exact=[user.username], then=Value(False)),
                default=Value(True),
                output_field=BooleanField(),
            )
        )
        .distinct()
    )
    # Ordering by random conflicts with the `distinct` statement in
    # sqlite as it adds a random number to every row that's used for ordering
    talks_list = list(talks.all())
    random.shuffle(talks_list)
    return talks_list


def is_user_allowed_to_vote(user):
    """
    Checks if user is allowed to vote at the moment of accessing this function
    This usually means checking if they have at least one ticket associated
    with their account (either for this or any of the past years
    """
    is_allowed = (
        #user.ticket_set.all().exists()
        user.ticket_set.filter(
            Q(frozen=False) &
            Q(fare__code__regex=fares.TALK_VOTING_CODE_REGEXP))
        or Talk.objects.proposed()
        .filter(created_by=user, conference=Conference.objects.current().code)
        .exists()
    )
    return is_allowed


@login_required
def vote_on_a_talk(request, talk_uuid):
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    current_conference = Conference.objects.current()
    if not current_conference.voting():
        return HttpResponseForbidden('Voting closed.')

    if not is_user_allowed_to_vote(request.user):
        return HttpResponseForbidden('Only users with tickets or talk proposals can vote this year.')

    # Users can't vote on their own talks.
    if (
        talk.created_by == request.user
        or talk.speakers.filter(pk=request.user.pk).exists()
        or talk.speakers.count() == 0
    ):
        return TemplateResponse(
            request,
            "conference/talk_voting/_voting_form.html",
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
                    "conference/talk_voting/_voting_form.html",
                    {"talk": talk, "db_vote": None, "VotingOptions": VotingOptions},
                )

            db_vote = VotoTalk.objects.create(user=request.user, talk=talk, vote=vote)

        if vote == VotingOptions.no_vote:
            db_vote.delete()
            return TemplateResponse(
                request,
                "conference/talk_voting/_voting_form.html",
                {"talk": talk, "db_vote": None, "VotingOptions": VotingOptions},
            )

        db_vote.vote = vote
        db_vote.save()

    return TemplateResponse(
        request,
        "conference/talk_voting/_voting_form.html",
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
    re_path(r"^$", talk_voting, name="talks"),
    re_path(r"^vote-on/(?P<talk_uuid>[\w]+)/$", vote_on_a_talk, name="vote"),
]
