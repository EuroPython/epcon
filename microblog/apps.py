import twitter

from django.apps import AppConfig
from django.db.models.signals import post_save


def truncate_headline(headline, n_char):
    last = headline[-n_char - 3]
    headline = headline[:-n_char -3]
    i = len(headline)
    while last not in " ,.;:" and i:
        i -= 1
        last = headline[i]
    if i != -1:
        headline = headline[:i]
    return headline + "..."

_twitter_template = Template(settings.MICROBLOG_TWITTER_MESSAGE_TEMPLATE)
def post_update_on_twitter(sender, instance, created, **kwargs):
    if settings.MICROBLOG_TWITTER_LANGUAGES is not None and instance.language not in settings.MICROBLOG_TWITTER_LANGUAGES:
        return
    post = instance.post
    if not post.is_published():
        return

    try:
        if not isinstance(settings.MICROBLOG_TWITTER_POST_URL_MANGLER, str):
            url = settings.MICROBLOG_TWITTER_POST_URL_MANGLER(instance)
        else:
            module, attr = settings.MICROBLOG_TWITTER_POST_URL_MANGLER.rsplit('.', 1)
            mod = import_module(module)
            url = getattr(mod, attr)(instance)
    except Exception, e:
        message = 'Post: "%s"\n\nCannot retrieve the url: "%s"' % (instance.headline, str(e))
        mail.mail_admins('[blog] error preparing the tweet', message)
        return

    existent = set(( x.value for x in Spam.objects.filter(post=post, method='t') ))
    recipients = set((settings.MICROBLOG_TWITTER_USERNAME,)) - existent
    if not recipients:
        return

    context = Context({
        'content': instance,
        'headline': instance.headline,
        'url': url,
    })
    status = _twitter_template.render(context)
    diff_len = len(status) - 140
    if diff_len > 0:
        context = Context({
            'content': instance,
            'headline': truncate_headline(instance.headline, diff_len),
            'url': url,
        })
        status = _twitter_template.render(context)
    if settings.MICROBLOG_TWITTER_DEBUG:
        print 'Tweet for', instance.headline.encode('utf-8')
        print status
        print '--------------------------------------------'
        return
    log.info('"%s" tweet on "%s"', instance.headline.encode('utf-8'), settings.MICROBLOG_TWITTER_USERNAME)
    try:
        api = twitter.Api(settings.MICROBLOG_TWITTER_USERNAME, settings.MICROBLOG_TWITTER_PASSWORD)
        api.PostUpdate(status)
        s = Spam(post=post, method='t', value=settings.MICROBLOG_TWITTER_USERNAME)
        s.save()
    except Exception, e:
        message = 'Post: "%s"\n\nCannot post status update: "%s"' % (instance.headline, str(e))
        mail.mail_admins('[blog] error tweeting the new status', message)
        return

def post_update_on_email(sender, instance, created, **kwargs):
    if settings.MICROBLOG_EMAIL_LANGUAGES is not None and instance.language not in settings.MICROBLOG_EMAIL_LANGUAGES:
        return
    post = instance.post
    if not post.is_published():
        return

    existent = set(( x.value for x in Spam.objects.filter(post=post, method='e') ))
    recipients = set(settings.MICROBLOG_EMAIL_RECIPIENTS) - existent
    if not recipients:
        return

    ctx = Context({
        'content': instance,
    })
    from django.utils.html import strip_tags
    from lxml import html
    from lxml.html.clean import clean_html

    subject = strip_tags(_email_templates['subject'].render(ctx))
    try:
        hdoc = html.fromstring(_email_templates['body'].render(ctx))
    except Exception, e:
        message = 'Post: "%s"\n\nCannot parse as html: "%s"' % (subject, str(e))
        mail.mail_admins('[blog] error while sending mail', message)
        return
    # dalla doc di lxml:
    # The module lxml.html.clean provides a Cleaner class for cleaning up
    # HTML pages. It supports removing embedded or script content, special
    # tags, CSS style annotations and much more.  Say, you have an evil web
    # page from an untrusted source that contains lots of content that
    # upsets browsers and tries to run evil code on the client side:
    #
    # Noi non dobbiamo proteggerci da codice maligno, ma vista la
    # situazione dei client email, possiamo rimuovere embed, javascript,
    # iframe.; tutte cose che non vengono quasi mai renderizzate per bene
    hdoc = clean_html(hdoc)

    # rendo tutti i link assoluti, in questo modo funzionano anche in un
    # client di posta
    hdoc.make_links_absolute(dsettings.DEFAULT_URL_PREFIX)

    body_html = html.tostring(hdoc)

    # per i client di posta che non supportano l'html ecco una versione in
    # solo testo
    import html2text
    h = html2text.HTML2Text()
    h.ignore_images = True
    body_text = h.handle(body_html)

    for r in recipients:
        log.info('"%s" email to "%s"', instance.headline.encode('utf-8'), r)
        email = mail.EmailMultiAlternatives(subject, body_text, dsettings.DEFAULT_FROM_EMAIL, [r])
        email.attach_alternative(body_html, 'text/html')
        email.send()
        s = Spam(post=post, method='e', value=r)
        s.save()

class MicroblogConfig(AppConfig):
    name = 'microblog'
    verbose_name = "Microblog"

    def ready(self):
        import moderation

        if settings.MICROBLOG_EMAIL_INTEGRATION:
            _email_templates = {
                'subject': Template(settings.MICROBLOG_EMAIL_SUBJECT_TEMPLATE),
                'body': Template(settings.MICROBLOG_EMAIL_BODY_TEMPLATE),
            }

            post_save.connect(post_update_on_email, sender=PostContent)

        if settings.MICROBLOG_TWITTER_INTEGRATION:
            post_save.connect(post_update_on_twitter, sender=PostContent)
