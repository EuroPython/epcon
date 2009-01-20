from django.db import models
from django.contrib.auth.models import User
import tagging
import tagging.fields

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class Post(models.Model):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'P', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    tags = tagging.fields.TagField()

    def __unicode__(self):
        return "Post of %s on %s" % (self.author, self.date)

    class Meta:
        ordering = ('-date',)
        get_latest_by = 'date'

class PostContent(models.Model):
    post = models.ForeignKey(Post)
    language = models.CharField(max_length = 3)
    headline = models.CharField(max_length = 200)
    slug = models.SlugField(unique_for_date = 'post.date')
    summary = models.TextField()
    body = models.TextField()

