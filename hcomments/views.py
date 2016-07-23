# -*- coding: UTF-8 -*-

from django import http
from django.conf import settings as dsettings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.comments.models import Comment
from django.contrib.comments import signals
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models.signals import post_save

from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.template.loader import render_to_string

from hcomments import get_form, models, settings


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

def post_comment(request):
    if request.method != 'POST':
        return http.HttpResponse(status=405)

    pk = request.POST['object_pk']

    content_type = request.POST['content_type']
    app_label, model = content_type.split('.', 1)

    ct = ContentType.objects.get(app_label=app_label, model=model)
    obj = ct.get_object_for_this_type(pk=pk)

    data = request.POST.copy()
    if request.user.is_authenticated():
        if not data.get('name', ''):
            data["name"] = request.user.get_full_name() or request.user.get_username()
        if not data.get('email', ''):
            data["email"] = request.user.email

    form = get_form(request)(obj, data)

    if not form.is_valid():
        return http.HttpResponse(content='TODO: errors', status=400)

    if form.security_errors():
        return http.HttpResponse(content='The comment form failed security verification: %s' % escape(str(form.security_errors())), status=400)

    comment = form.get_comment_object()
    comment.ip_address = request.META.get("REMOTE_ADDR", None)

    if request.user.is_authenticated():
        comment.user = request.user

    responses = signals.comment_will_be_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request
    )

    for (receiver, response) in responses:
        if response is False:
            return http.HttpResponse(content='comment_will_be_posted receiver %r killed the comment' % receiver.__name__, status=400)

    # Save the comment and signal that it was saved
    comment.save()
    signals.comment_was_posted.send(
        sender=comment.__class__,
        comment=comment,
        request=request
    )

    if not comment.is_public:
        return http.HttpResponse(content='moderated', status=403)

    s = request.session.get('user-comments', [])
    s = set(s)
    s.add(comment.pk)

    request.session['user-comments'] = list(s)

    return render_to_response(
        'hcomments/show_single_comment.html', {
            'c': comment,
            'owner': True,
        },
        context_instance=RequestContext(request)
    )


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
