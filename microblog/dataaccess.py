# -*- coding: UTF-8 -*-

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
import functools
import hashlib

WEEK = 7 * 24 * 60 * 60 # 1 week
def cache_me(key=None, ikey=None, signals=(), models=(), timeout=WEEK):
    def hashme(k):
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        return hashlib.md5(k).hexdigest()
    def decorator(f):

        def invalidate(sender, **kwargs):
            if ikey is None:
                ks = (f.__name__,)
            elif callable(ikey):
                k = ikey(sender, **kwargs)
                if isinstance(k, basestring):
                    ks = (k,)
                else:
                    ks = k
            else:
                ks = (ikey,)
            if ks:
                cache.delete_many(map(hashme, ks))

        if ikey or (ikey is None and key is None):
            for s in signals:
                s.connect(invalidate, weak=False)

            for m in models:
                post_save.connect(invalidate, sender=m, weak=False)
                post_delete.connect(invalidate, sender=m, weak=False)

        def _key(*args, **kwargs):
            if key is None:
                k = f.__name__
            elif callable(key):
                k = key(*args, **kwargs)
            else:
                k = key % args
            return hashme(k)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            k = _key(*args, **kwargs)
            data = cache.get(k)
            if data is None:
                data = f(*args, **kwargs)
                cache.set(k, data, timeout)
            return data
        wrapper.cachekey = _key
            
        return wrapper
    return decorator

from collections import defaultdict
from django.conf import settings as dsettings
from django.contrib import comments
from django.core.urlresolvers import reverse
from microblog import models
from microblog import settings
from taggit.models import TaggedItem

def _i_post_list(sender, **kw):
    ks = []
    for l in dsettings.LANGUAGES:
        ks.append('m:post_list:%s' % l[0])
    return ks
@cache_me(models=(models.Post,),
    key='m:post_list:%s',
    ikey=_i_post_list)
def post_list(lang):
    qs = models.Post.objects\
        .all()\
        .byLanguage(lang)\
        .order_by('-date')\
        .select_related('category', 'author')
    return list(qs)

@cache_me(models=(models.Post,))
def tag_map():
    tmap = defaultdict(set)
    items = TaggedItem.objects\
        .filter(content_type__app_label='microblog', content_type__model='post')\
        .select_related('tag')
    for o in items:
        tmap[o.object_id].add(o.tag)
    return tmap

@cache_me(models=(models.Post,),
           key = 'm:tagged_posts:%s',
           ikey = 'm:tagged_posts:%s')
def tagged_posts(name):
    """
    restituisce i post taggati con il tag passato
    """
    posts = TaggedItem.objects\
        .filter(content_type__app_label='microblog', content_type__model='post')\
        .filter(tag__name__iexact=name)\
        .values_list('object_id', flat=True)
    return set(posts)

def _i_post_data(sender, **kw):
    if sender is models.Post:
        pid = kw['instance'].id
    elif sender is comments.get_model():
        o = kw['instance']
        if o.content_type.app_label == 'microblog' and o.content_type.model == 'post':
            pid = o.object_pk
        else:
            pid = None
    else:
        pid = kw['instance'].post_id
    ks = []
    if pid:
        for l in dsettings.LANGUAGES:
            ks.append('m:post_data:%s%s' % (pid, l[0]))
    return ks
@cache_me(models=(models.Post, models.PostContent, comments.get_model()),
    key='m:post_data:%s%s',
    ikey=_i_post_data)
def post_data(pid, lang):
    post = models.Post.objects\
        .select_related('author', 'category')\
        .get(id=pid)
    try:
        content = post.content(lang=lang, fallback=True)
    except models.PostContent.DoesNotExist:
        content = None

    comment_list = comments.get_model().objects\
        .filter(content_type__app_label='microblog', content_type__model='post')\
        .filter(object_pk=pid, is_public=True)

    burl = models.PostContent.build_absolute_url(post, content)
    return {
        'post': post,
        'content': content,
        'url': dsettings.DEFAULT_URL_PREFIX + reverse(burl[0], args=burl[1], kwargs=burl[2]),
        'comments': list(comment_list),
        'tags': list(post.tags.all()),
    }

def _i_get_reactions(sender, **kw):
    if sender is models.Trackback:
        return 'm:reaction:%s' % kw['instance'].content_id
    else:
        return 'm:reaction:%s' % kw['instance'].object_id
if settings.MICROBLOG_PINGBACK_SERVER:
    deco = cache_me(models=(models.Trackback,),
        key='m:reactions:%s',
        ikey=_i_get_reactions)
else:
    from pingback.models import Pingback
    deco = cache_me(models=(models.Trackback, Pingback),
        key='m:reactions:%s',
        ikey=_i_get_reactions)
@deco
def get_reactions(cid):
    trackbacks = models.Trackback.objects.filter(content=cid)
    if settings.MICROBLOG_PINGBACK_SERVER:
        from pingback.models import Pingback
        # Purtroppo il metodo pingbacks_for_object vuole un oggetto non un id
        content = models.PostContent.objects.get(id=cid)
        pingbacks = Pingback.objects.pingbacks_for_object(content).filter(approved=True)
    else:
        pingbacks = []
    reactions = sorted(list(trackbacks) + list(pingbacks), key=lambda r: r.date, reverse=True)
    # normalizzo le reactions, mi assicuro che tutte abbiano un excerpt
    for ix, r in enumerate(reactions):
        if not hasattr(r, 'excerpt'):
            r.excerpt = r.content
    return reactions
