# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.contrib.auth import models as authModels
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, Http404
from django.shortcuts import render, render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify

from microblog import models, settings

from taggit.models import Tag, TaggedItem
from decorator import decorator

try:
    import json
except ImportError:
    import simplejson as json

def render_json(f):
    """
    decoratore da applicare ad una vista per serializzare in json il risultato.
    """
    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: json.dumps(d, indent=2)
    else:
        ct = 'application/json'
        j = json.dumps
    def wrapper(func, *args, **kw):
        try:
            result = func(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, HttpResponse):
                return result
            else:
                result = j(result)
                status = 200
        return HttpResponse(content=result, content_type=ct, status=status)
    return decorator(wrapper, f)

def post_list(request):
    return render(request, 'microblog/post_list.html', {})

def category(request, category):
    category = get_object_or_404(models.Category, name=category)
    return render_to_response(
        'microblog/category.html',
        {
            'category': category,
        },
        context_instance=RequestContext(request)
    )

def post_list_by_year(request, year, month=None):
    return render_to_response(
        'microblog/list_by_year.html',
        {
            'year': year,
            'month': month,
        },
        context_instance=RequestContext(request)
    )

def tag(request, tag):
    tag = get_object_or_404(Tag, name=tag)
    return render_to_response(
        'microblog/tag.html',
        {
            'tag': tag,
        },
        context_instance=RequestContext(request)
    )

def author(request, author):
    user = [
        u for u in authModels.User.objects.all()
        if slugify('%s-%s' % (u.first_name, u.last_name)) == author
    ]
    if not user:
        raise Http404()
    else:
        user = user[0]

    return render_to_response(
        'microblog/author.html',
        {
            'author': user,
        },
        context_instance=RequestContext(request)
    )

def _paginate_posts(post_list, request):
    if settings.MICROBLOG_POST_LIST_PAGINATION:
        paginator = Paginator(post_list, settings.MICROBLOG_POST_PER_PAGE)
        try:
            page = int(request.GET.get("page", "1"))
        except ValueError:
            page = 1

        try:
            posts = paginator.page(page)
        except (EmptyPage, InvalidPage):
            posts = paginator.page(1)
    else:
        paginator = Paginator(post_list, len(post_list) or 1)
        posts = paginator.page(1)

    return posts

def _posts_list(request, featured=False):
    if settings.MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST:
        lang = None
    else:
        lang = request.LANGUAGE_CODE

    return models.Post.objects\
        .byLanguage(lang)\
        .byFeatured(featured)\
        .published()

def _post_detail(request, content):
    if not settings.MICROBLOG_POST_FILTER([content.post], request.user):
        raise Http404()
    return render_to_response(
        'microblog/post_detail.html',
        {
            'post': content.post,
            'content': content
        },
        context_instance=RequestContext(request)
    )

def _trackback_ping(request, content):
    def success():
        x = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<response><error>0</error></response>')
        return HttpResponse(content=x, content_type='text/xml')

    def failure(message=''):
        x = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<response><error>1</error><message>%s</message></response>') % message
        return HttpResponse(content=x, content_type='text/xml', status=400)

    if request.method != 'POST':
        return failure('only POST method is supported')

    if not request.POST.get('url'):
        return failure('url argument is mandatory')

    t = {
        'url': request.POST['url'],
        'blog_name': request.POST.get('blog_name', ''),
        'title': request.POST.get('title', ''),
        'excerpt': request.POST.get('excerpt', ''),
    }

    from microblog.moderation import moderate
    if not moderate(request, 'trackback', t['title'], url=t['url']):
        return failure('moderated')

    content.new_trackback(**t)
    return success()

@render_json
def _comment_count(request, content):
    post = content.post
    if settings.MICROBLOG_COMMENT == 'comment':
        import django_comments as comments
        from django.contrib.contenttypes.models import ContentType
        model = comments.get_model()
        q = model.objects.filter(
            content_type=ContentType.objects.get_for_model(post),
            object_pk=post.id,
            is_public=True
        )
        return q.count()
    else:
        import httplib2
        from urllib import quote
        h = httplib2.Http()
        params = {
            'forum_api_key': settings.MICROBLOG_COMMENT_DISQUS_FORUM_KEY,
            'url': content.get_url(),
        }
        args = '&'.join('%s=%s' % (k, quote(v)) for k, v in params.items())
        url = settings.MICROBLOG_COMMENT_DISQUS_API_URL + 'get_thread_by_url?%s' % args

        resp, page = h.request(url)
        if resp.status != 200:
            return -1
        page = json.loads(page)
        if not page['succeeded']:
            return -1
        elif page['message'] is None:
            return 0
        else:
            return page['message']['num_comments']

def _post404(f):
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except models.PostContent.DoesNotExist:
            raise Http404()
    return wrapper

if settings.MICROBLOG_URL_STYLE == 'date':
    def _get(slug, year, month, day):
        return models.PostContent.objects\
            .select_related('post')\
            .getBySlugAndDate(slug, year, month, day)
    @_post404
    def post_detail(request, year, month, day, slug):
        return _post_detail(
            request,
            content=_get(slug, year, month, day)
        )

    @_post404
    def trackback_ping(request, year, month, day, slug):
        return _trackback_ping(
            request,
            content=_get(slug, year, month, day)
        )

    @_post404
    def comment_count(request, year, month, day, slug):
        return _comment_count(
            request,
            content = _get(slug, year, month, day)
        )
elif settings.MICROBLOG_URL_STYLE == 'category':
    def _get(slug, category):
        return models.PostContent.objects\
            .select_related('post')\
            .getBySlugAndCategory(slug, category)
    @_post404
    def post_detail(request, category, slug):
        return _post_detail(
            request,
            content=_get(slug, category),
        )

    @_post404
    def trackback_ping(request, category, slug):
        return _trackback_ping(
            request,
            content=_get(slug, category),
        )

    @_post404
    def comment_count(request, category, slug):
        return _comment_count(
            request,
            content=_get(slug, category),
        )
