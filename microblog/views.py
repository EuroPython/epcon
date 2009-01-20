import datetime
from microblog import models

def post(request, year, month, day, slug):
    postcontent = models.PostContent.objects.get(
        slug = slug, 
        post__date__year = int(year),
        post__date__month = int(month),
        post__date__day = int(day)
    )
    print postcontent
    return ''
