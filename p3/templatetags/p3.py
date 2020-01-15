from django import template
from django.conf import settings

from p3 import dataaccess

register = template.Library()


@register.simple_tag()
def p3_profile_data(uid):
    return dataaccess.profile_data(uid)

@register.simple_tag(takes_context=True)
def all_user_tickets(context, uid=None, conference=None,
                     status="complete", fare_type="conference"):
    if uid is None:
        uid = context['request'].user.id
    if conference is None:
        conference = settings.CONFERENCE_CONFERENCE
    tickets = dataaccess.all_user_tickets(uid, conference)
    if status == 'complete':
        tickets = [x for x in tickets if x[3]]
    elif status == 'incomplete':
        tickets = [x for x in tickets if not x[3]]
    if fare_type != "all":
        tickets = [x for x in tickets if x[1] == fare_type]

    return tickets

@register.simple_tag()
def p3_tags():
    return dataaccess.tags()
