from django.views.generic import ListView

from .models import News


class NewsList(ListView):
    model = News
    paginate_by = 100
    template_name = "conference/news/list.html"
    context_object_name = "news"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Latest News"
        return context

    def get_queryset(self):
        return News.objects.filter(status=News.STATUS.PUBLISHED)


news_list = NewsList.as_view()
