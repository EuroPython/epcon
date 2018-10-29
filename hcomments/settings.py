# -*- coding: utf-8 -*-
from django.conf import settings

# callable invoked in order to determine if the current user can moderate the comment.
MODERATOR_REQUEST = getattr(settings, 'HCOMMENTS_MODERATOR_REQUEST', lambda request, comment: request.user.is_superuser)

# callable invoked to identify the thread's owners, should return None or a list of users.
THREAD_OWNERS = getattr(settings, 'HCOMMENTS_THREAD_OWNERS', lambda o: None)
