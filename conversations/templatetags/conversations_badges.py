from django import template

from conversations.models import Thread

register = template.Library()


@register.simple_tag
def status_badge_class(status):
    """
    Mapping Thread statuses to bootstrap badges
    """

    if status in [Thread.STATUS.COMPLETED]:
        return 'dark'

    if status in [Thread.STATUS.NEW, Thread.STATUS.REOPENED,
                  Thread.STATUS.USER_REPLIED]:
        return 'primary'

    return 'success'


@register.simple_tag
def priority_badge_class(status):
    """
    Mapping Thread priorities to bootstrap badges
    """

    if status == Thread.PRIORITIES.LOW:
        return 'dark'

    if status == Thread.PRIORITIES.MEDIUM:
        return 'success'

    if status == Thread.PRIORITIES.HIGH:
        return 'danger'
