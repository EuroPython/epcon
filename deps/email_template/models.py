# -*- coding: UTF-8 -*-
from django.db import models
from django.template import Template, Context
from django.utils.safestring import mark_safe

class Email(models.Model):
    code = models.CharField('Codice', max_length = 30,
        unique = True,
        help_text = 'codice testuale che identifica in maniera univoca questa email')
    subject = models.CharField('Oggetto', max_length = 200)
    text = models.TextField('Testo')
    from_email = models.CharField('From address', max_length = 200, blank = True)
    cc = models.TextField('Cc address', blank = True)
    bcc = models.TextField('Bcc address', blank = True)

    def __unicode__(self):
        return 'email_template: %s' % self.code

    def render(self, ctx, mark_safestring=True):
        """
        Restituisce subject e body dopo averci applicato il contesto
        passato.
        """
        if mark_safestring:
            ctx = dict(ctx)
            for key, value in ctx.items():
                if isinstance(value, basestring):
                    ctx[key] = mark_safe(value)
        ctx = Context(ctx)
        return Template(self.subject).render(ctx), Template(self.text).render(ctx)
