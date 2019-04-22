# -*- coding: utf-8 -*-

from django import http
from django_comments.forms import CommentForm
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.utils.html import escape
from django.shortcuts import render_to_response


@login_required
def post_comment(request):
    if request.method != 'POST':
        return http.HttpResponse(status=405)
    pk = request.POST['object_pk']

    content_type = request.POST['content_type']
    app_label, model = content_type.split('.', 1)

    ct = ContentType.objects.get(app_label=app_label, model=model)
    obj = ct.get_object_for_this_type(pk=pk)

    data = request.POST.copy()
    data["name"] = request.user.get_full_name() or request.user.get_username()
    data["email"] = request.user.email

    form = CommentForm(obj, data)

    if not form.is_valid():
        return http.HttpResponse(content='TODO: errors', status=400)

    if form.security_errors():
        return http.HttpResponse(content='The comment form failed security verification: %s' % escape(str(form.security_errors())), status=400)

    comment = form.get_comment_object()
    comment.ip_address = request.META.get("REMOTE_ADDR", None)
    comment.user = request.user

    comment.save()

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
    )
