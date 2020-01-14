import os.path

from django import http
from django.conf import settings as dsettings

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from common.decorators import render_to_json
from conference import models, settings
from conference.decorators import profile_access


class HttpResponseRedirectSeeOther(http.HttpResponseRedirect):
    status_code = 303


def talk(request, slug):
    return redirect('talks:talk', permanent=True, talk_slug=slug)


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
