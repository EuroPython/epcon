# -*- coding: utf-8 -*-
from p3.models import P3Talk


def moderator_requests(request, comment):
    if request.user.is_superuser:
        return True
    else:
        owners = thread_owners(comment.content_object)
        if owners:
            return request.user in owners
    return False


def thread_owners(instance):
    if isinstance(instance, P3Talk):
        return [s.user for s in instance.get_all_speakers()]
    return None
