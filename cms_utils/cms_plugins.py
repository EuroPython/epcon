from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import MarkitUpPluginModel, TemplatePluginModel


@plugin_pool.register_plugin
class MarkItUpPlugin(CMSPluginBase):
    name = _('MarkItUp')
    model = MarkitUpPluginModel
    render_template = 'djangocms_markitup/markitup.html'


@plugin_pool.register_plugin
class TemplatePlugin(CMSPluginBase):
    name = _('Template Plugin')
    model = TemplatePluginModel
    render_template = 'djangocms_template/template_plugin.html'
