import sys
sys.path.append(r'C:\Data\Webs\pycontre\pycon_site\deps')


BASE = 'C:/Data/Webs/pycontre/pycon_site'

TEMPLATE_DIRS = (
 BASE + '/p3/templates',
)
P3_STATIC_DIR = BASE + '/p3/static'
P3_STUFF_DIR = BASE + '/stuff'

MEDIA_ROOT = BASE + '/deps/pages/media/'

del BASE