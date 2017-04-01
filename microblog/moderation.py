# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.urlresolvers import reverse
from django_comments.moderation import CommentModerator, moderator

from microblog import settings
from microblog.models import Post

def moderate(request, type, text, user='', email='', url=''):
    if settings.MICROBLOG_MODERATION_TYPE == 'akismet':
        import akismet
        aks = akismet.Akismet(
            agent='Microblog',
            key=settings.MICROBLOG_AKISMET_KEY,
            blog_url=dsettings.DEFAULT_URL_PREFIX + reverse('microblog-full-list')
        )
        try:
            if aks.verify_key():
                m = request.META
                data = {
                    'user_ip': m['REMOTE_ADDR'],
                    'user_agent': m.get('HTTP_USER_AGENT', ''),
                    'referrer': m.get('HTTP_REFERER', ''),
                    'comment_type': type,
                    'comment_author': user,
                    'comment_author_email': email,
                    'comment_author_url': url,
                    'HTTP_ACCEPT': m.get('HTTP_ACCEPT', ''),
                    'permalink': '',
                    'SERVER_NAME': m.get('SERVER_NAME', ''),
                    'SERVER_SOFTWARE': m.get('SERVER_SOFTWARE', ''),
                    'SERVER_ADMIN': m.get('SERVER_ADMIN', ''),
                    'SERVER_ADDR': m.get('SERVER_ADDR', ''),
                    'SERVER_SIGNATURE': m.get('SERVER_SIGNATURE', ''),
                    'SERVER_PORT': m.get('SERVER_PORT', ''),
                }
                r = aks.comment_check(text.encode('utf-8'), data, build_data=False)
            else:
                raise ValueError('Akismet: invalid key')
        except:
            if dsettings.DEBUG:
                raise
    elif settings.MICROBLOG_MODERATION_TYPE == 'always':
        return True
    else:
        return False

class PostModeration(CommentModerator):
    email_notification = True
    enable_field = 'allow_comments'
    auto_moderate_field = 'date'
    moderate_after = 30

    def moderate(self, comment, content_object, request):
        r = super(PostModeration, self).moderate(comment, content_object, request)
        if not r:
            r = moderate(request, 'comment', comment.comment, user=comment.user_name, email=comment.user_email, url=comment.user_url)
        return r

if settings.MICROBLOG_MODERATION_TYPE:
    moderator.register(Post, PostModeration)
