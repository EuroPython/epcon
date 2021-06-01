from cms.api import add_plugin, create_page
from cms.test_utils.testcases import CMSTestCase
from cms_utils.cms_plugins import TemplatePlugin


class CmsPluginsTestCase(CMSTestCase):
    def test_template_plugin(self):
        page = create_page(
            title='test',
            template='conference/homepage/home_template.html',
            language='en',
        )
        placeholder = page.placeholders.get(slot="text")
        plugin = add_plugin(
            placeholder=placeholder,
            plugin_type=TemplatePlugin.__name__,
            language='en',
            body='<script>XSS</script>{% comment %}THIS IS JUST A COMMENT{% endcomment %}',
        )
        assert plugin.plugin_type == 'TemplatePlugin'
        assert plugin.full_clean() is None

        page.publish('en')
        url = page.get_absolute_url('en')
        assert url == '/test/'

        response = self.client.get(url)
        print(response.content)

        # Django Template evaluated?
        self.assertNotContains(response, 'THIS IS JUST A COMMENT')

        # Nothing escaped?
        self.assertContains(response, '<script>XSS</script>')
