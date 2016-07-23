# -*- coding: UTF-8 -*-
import urlparse

try:
    parse_qs = urlparse.parse_qs
except AttributeError:
    from cgi import parse_qs

from django import http
from django.conf import settings as dsettings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.comments.models import Comment
from django.contrib.comments.signals import comment_will_be_posted
from django.contrib.comments.views import comments as comments_views
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.template.loader import render_to_string

from hcomments import models
from hcomments import settings


def send_email_to_subscribers(sender, **kwargs):
    subscripted = models.ThreadSubscription.objects.subscriptions(kwargs['instance'].content_object)
    for u in filter(lambda x: x.email, subscripted):
        ctx = {
            'comment': kwargs['instance'],
            'object': kwargs['instance'].content_object,
            'user': u,
        }
        subject = 'New comment on a subscribed page'
        body = render_to_string('hcomments/thread_email.txt', ctx)
        send_mail(subject, body, dsettings.DEFAULT_FROM_EMAIL, [u.email])

post_save.connect(send_email_to_subscribers, sender=Comment)
post_save.connect(send_email_to_subscribers, sender=models.HComment)


class CaptchaFailed(Exception):
    pass


def on_comment_will_be_posted(sender, **kw):
    if sender is not models.HComment:
        return True

    # if comments is configured to use a captcha we need another validation step
    import hcomments
    request = kw['request']
    comment = kw['comment']

    data = request.POST.copy()
    if request.user.is_authenticated():
        if not data.get('name', ''):
            data["name"] = request.user.get_full_name() or request.user.get_username()
        if not data.get('email', ''):
            data["email"] = request.user.email
    form = hcomments.get_form(request)(comment, data)
    if not form.is_valid():
        raise CaptchaFailed()
    return True

comment_will_be_posted.connect(on_comment_will_be_posted)


def post_comment(request):
    from recaptcha_works.decorators import fix_recaptcha_remote_ip
    try:
        result = fix_recaptcha_remote_ip(comments_views.post_comment)(request)
    except CaptchaFailed:
        result = None

    if 'async' not in request.POST:
        if result:
            return result
        else:
            return comments_views.CommentPostBadRequest('')

    if result is None:
        return http.HttpResponse(content='captcha', status=403)

    if isinstance(result, comments_views.CommentPostBadRequest):
        return http.HttpResponseBadRequest('')

    # since post_comment returns a HttpResponse, the only way to determine
    # the comment that has just been posted is to analyze the Location header

    try:
        loc = result['Location']
    except:
        return http.HttpResponseBadRequest('')

    try:
        url = urlparse.urlsplit(loc)
        cid = parse_qs(url.query).get('c')
        try:
            cid = int(cid[0])
            comment = models.HComment.objects.get(pk=cid)
        except:
            comment = None
        else:
            if not comment.is_public:
                return http.HttpResponse(content='moderated', status=403)
            s = request.session.get('user-comments', [])
            s = set(s)
            s.add(cid)
            request.session['user-comments'] = list(s)
        return render_to_response(
            'hcomments/show_single_comment.html', {
                'c': comment,
                'owner': True,
            },
            context_instance=RequestContext(request)
        )
    except Exception, e:
        if dsettings.DEBUG:
            return http.HttpResponseBadRequest(str(e))
        else:
            raise


def delete_comment(request):
    if request.method != 'POST':
        return http.HttpResponseBadRequest()
    try:
        cid = int(request.POST['cid'])
    except:
        raise http.HttpResponseBadRequest()
    try:
        comment = models.HComment.objects.get(pk=cid)
    except models.HComment.DoesNotExist:
        return http.HttpResponse('')

    s = request.session.get('user-comments', [])
    if cid not in s:
        if not settings.MODERATOR_REQUEST(request, comment):
            raise http.HttpResponseBadRequest()
    else:
        s = set(s)
        s.remove(cid)
        request.session['user-comments'] = s
    comment.delete()
    return http.HttpResponse('')


def subscribe(request):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))
    if not request.user.is_authenticated():
        return http.HttpResponseBadRequest()
    content_type = request.POST['content_type']
    object_pk = request.POST['object_pk']

    app_label, model = content_type.split('.', 1)
    ct = ContentType.objects.get(app_label=app_label, model=model)
    object = ct.get_object_for_this_type(pk=object_pk)
    if 'subscribe' in request.POST:
        models.ThreadSubscription.objects.subscribe(object, request.user)
    elif 'unsubscribe' in request.POST:
        models.ThreadSubscription.objects.unsubscribe(object, request.user)

    return redirect(request.META.get('HTTP_REFERER', '/'))


@staff_member_required
def moderate_comment(request, cid, public=False):
    try:
        comment = get_object_or_404(models.HComment, pk=int(cid))
    except (TypeError, ValueError):
        return http.HttpResponseBadRequest()
    comment.is_public = public
    comment.save()
    return http.HttpResponse(content='done', status=200)
