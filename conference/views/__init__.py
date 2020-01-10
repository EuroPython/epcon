import os.path

from django import http
from django.conf import settings as dsettings

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect, render_to_response

from common.decorators import render_to_json
from common.decorators import render_to_template
from conference import models, settings
from conference.decorators import speaker_access, talk_access, profile_access
from conference.forms import SpeakerForm, TalkForm


class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303


@speaker_access
@render_to_template('conference/speaker.html')
def speaker(request, slug, speaker, talks, full_access, speaker_form=SpeakerForm):
    if request.method == 'POST':
        if not full_access:
            return http.HttpResponseBadRequest()
        form = speaker_form(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            speaker.activity = data['activity']
            speaker.activity_homepage = data['activity_homepage']
            speaker.industry = data['industry']
            speaker.company = data['company']
            speaker.company_homepage = data['company_homepage']
            speaker.save()
            speaker.setBio(data['bio'])
            return HttpResponseRedirectSeeOther(reverse('conference-speaker', kwargs={'slug': speaker.slug}))
    else:
        form = speaker_form(initial={
            'activity': speaker.activity,
            'activity_homepage': speaker.activity_homepage,
            'industry': speaker.industry,
            'company': speaker.company,
            'company_homepage': speaker.company_homepage,
            'bio': getattr(speaker.getBio(), 'body', ''),
        })
    return {
        'form': form,
        'full_access': full_access,
        'speaker': speaker,
        'talks': talks,
        'accepted': talks.filter(status='accepted'),
    }


def talk(request, slug):
    return redirect('talks:talk', permanent=True, talk_slug=slug)


@render_to_template('conference/talk_preview.html')
@talk_access
def talk_preview(request, slug, talk, full_access, talk_form=TalkForm):
    conf = models.Conference.objects.current()
    return {
        'talk': talk,
        'voting': conf.voting(),
    }


def talk_video(request, slug):  # pragma: no cover
    tlk = get_object_or_404(models.Talk, slug=slug)

    if not tlk.video_type or tlk.video_type == 'download':
        if tlk.video_file:
            vurl = dsettings.MEDIA_URL + tlk.video_file.url
            vfile = tlk.video_file.path
        elif settings.VIDEO_DOWNLOAD_FALLBACK:
            for ext in ('.avi', '.mp4'):
                fpath = os.path.join(dsettings.MEDIA_ROOT, 'conference/videos', tlk.slug + ext)
                if os.path.exists(fpath):
                    vurl = dsettings.MEDIA_URL + 'conference/videos/' + tlk.slug + ext
                    vfile = fpath
                    break
            else:
                raise http.Http404()
        else:
            raise http.Http404()
    else:
        raise http.Http404()

    if settings.TALK_VIDEO_ACCESS:
        if not settings.TALK_VIDEO_ACCESS(request, tlk):
            return http.HttpResponseForbidden()

    vext = os.path.splitext(vfile)[1]
    if vext == '.mp4':
        mt = 'video/mp4'
    elif vext == '.avi':
        mt = 'video/x-msvideo'
    else:
        mt = None
    if settings.X_SENDFILE is None:
        r = http.HttpResponse(file(vfile), content_type=mt)
    elif settings.X_SENDFILE['type'] == 'x-accel':
        r = http.HttpResponse('', content_type=mt)
        r['X-Accel-Redirect'] = vurl
    elif settings.X_SENDFILE['type'] == 'custom':
        return settings.X_SENDFILE['f'](tlk, url=vurl, fpath=vfile, content_type=mt)
    else:
        raise RuntimeError('invalid X_SENDFILE')
    fname = '%s%s' % (tlk.title.encode('utf-8'), vext.encode('utf-8'))
    r['content-disposition'] = 'attachment; filename="%s"' % fname
    return r


def talk_report(request):  # pragma: no cover
    conference = request.GET.getlist('conference')
    tags = request.GET.getlist('tag')
    return render_to_response(
        'conference/talk_report.html', {
            'conference': conference,
            'tags': tags,
        },
    )


@render_to_json
def sponsor_json(request, sponsor):
    """
    Returns the data of the requested sponsor
    """
    sponsor = get_object_or_404(models.Sponsor, slug=sponsor)
    return {
        'sponsor': sponsor.sponsor,
        'slug': sponsor.slug,
        'url': sponsor.url
    }


@profile_access
def user_profile(request, slug, profile=None, full_access=False):
    return redirect('profiles:profile', profile_slug=slug)


@login_required
def myself_profile(request):
    p = models.AttendeeProfile.objects.getOrCreateForUser(request.user)
    return redirect('conference-profile', slug=p.slug)
