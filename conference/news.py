
from django.views.generic import ListView

from .models import News


class NewsList(ListView):
    model = News
    paginate_by = 100
    template_name = 'ep19/bs/news/list.html'
    context_object_name = "news"

    def get_queryset(self):
        return News.objects.filter(status=News.STATUS.PUBLISHED)


news_list = NewsList.as_view()
