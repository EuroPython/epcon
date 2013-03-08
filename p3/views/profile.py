# -*- coding: UTF-8 -*-
import os.path
import logging
from assopy import models as amodels
from assopy.views import render_to_json
from conference import models as cmodels
from conference.views import profile_access, json_dumps
from django import http
from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from email_template import utils
from p3 import dataaccess
from p3 import forms as p3forms
from p3 import models

log = logging.getLogger('p3.views')

@profile_access
def p3_profile(request, slug, profile=None, full_access=False, format_='html'):
    if format_ == 'json':
        pdata = dataaccess.profile_data(profile.user_id)
        from conference.templatetags.conference import markdown2
        pdata['bio'] = markdown2(pdata['bio'], "smarty-pants,code-color")
        return http.HttpResponse(
            json_dumps(pdata),
            content_type='text/javascript')
    tpl = 'conference/profile_publicdata_form.html'
    if request.method == 'POST':
        section = request.POST.get('section')
        if section == 'public-data':
            fc = p3forms.P3ProfilePublicDataForm
            tpl = 'conference/profile_publicdata_form.html'
        elif section == 'bio':
            fc = p3forms.P3ProfileBioForm
            tpl = 'conference/profile_bio_form.html'
        elif section == 'visibility':
            fc = p3forms.P3ProfileVisibilityForm
            tpl = 'conference/profile_visibility_form.html'
        elif section == 'picture':
            fc = p3forms.P3ProfilePictureForm
            tpl = 'conference/profile_picture_form.html'
        else:
            fc = p3forms.P3ProfileForm
        form = fc(instance=profile, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save()
    else:
        form = p3forms.P3ProfileForm(instance=profile)
    ctx = {
        'form': form,
        'full_access': full_access,
        'profile': profile,
    }
    return render(request, tpl, ctx)

def p3_profile_avatar(request, slug):
    p = get_object_or_404(cmodels.AttendeeProfile, slug=slug).p3_profile
    from urllib2 import urlopen
    try:
        img = urlopen(p.profile_image_url(anonymous=False))
    except Exception:
        path = os.path.join(os.path.dirname(p3.__file__), 'static', settings.P3_ANONYMOUS_AVATAR)
        img = file(path)
        ct = 'image/jpg'
    else:
        headers = img.info()
        ct = headers.get('content-type')
    return http.HttpResponse(img.read(), content_type=ct)

@login_required
@render_to_json
def p3_profile_message(request, slug):
    if request.method != 'POST':
        return http.HttpResponseNotAllowed(('POST',))

    class MessageForm(forms.Form):
        subject = forms.CharField()
        message = forms.CharField()

    f = MessageForm(data=request.POST)
    if f.is_valid():
        data = f.cleaned_data
        profile = get_object_or_404(cmodels.AttendeeProfile, slug=slug)
        try:
            profile.p3_profile.send_user_message(request.user, data['subject'], data['message'])
        except ValueError, e:
            return http.HttpResponseBadRequest(str(e))
        return "OK"
    return f.errors

@login_required
def p3_account_data(request):
    ctx = {}
    if request.method == 'POST':
        profile = cmodels.AttendeeProfile.objects.getOrCreateForUser(request.user)
        form = p3forms.P3ProfilePersonalDataForm(instance=profile, data=request.POST)
        ctx['pform'] = form
        if form.is_valid():
            form.save()
            data = form.cleaned_data
            request.user.first_name = data['first_name']
            request.user.last_name = data['last_name']
            request.user.save()
            if profile.slug[0] == '-':
                slug = cmodels.AttendeeProfile.objects.findSlugForUser(request.user)
                if slug and slug[0] != '-':
                    profile.slug = slug
                    profile.save()
    return render(request, "assopy/profile_personal_data.html", ctx)

@transaction.commit_on_success
def OTCHandler_E(request, token):
    user = token.user
    models.TicketConference.objects\
        .filter(assigned_to=user.email)\
        .update(assigned_to=token.payload)
    user.email = token.payload
    user.save()
    log.info('"%s" has verified the new email "%s"', user.username, user.email)
    return redirect('assopy-profile')

@login_required
def p3_account_email(request):
    ctx = {}
    if request.method == 'POST':
        form = p3forms.P3ProfileEmailContactForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if email != request.user.email:
                log.info(
                    'requested an email change from "%s" to "%s" for the user "%s"',
                    request.user.email,
                    email,
                    request.user.username,)
                utils.email(
                    'verify-account',
                    ctx={
                        'user': request.user,
                        'token': amodels.Token.objects.create(ctype='e', user=request.user, payload=email),
                    },
                    to=[email]
                ).send()
    return render(request, "assopy/profile_email_contact.html", ctx)

@login_required
def p3_account_spam_control(request):
    ctx = {}
    if request.method == 'POST':
        profile = cmodels.AttendeeProfile.objects.getOrCreateForUser(request.user)
        form = p3forms.P3ProfileSpamControlForm(instance=profile.p3_profile, data=request.POST)
        if form.is_valid():
            form.save()
    return render(request, "assopy/profile_spam_control.html", ctx)
