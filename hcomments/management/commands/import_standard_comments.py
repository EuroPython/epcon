from django.db import connection, transaction
from django_comments.models import Comment
from django.core.management.base import BaseCommand

from hcomments.models import HComment


class Command(BaseCommand):
    help = "Import the standard comments into hcomments"

    @transaction.atomic
    def handle(self, *args, **options):
        """
        Converts all legacy Comment objects into HComment objects.
        """
        sql = """
        INSERT INTO hcomments_hcomment(comment_ptr_id, parent_id, lft, rght, tree_id, level)
        VALUES (%s, NULL, 1, 2, %s, 0)
        """
        hcomments = dict(((c.id, c) for c in HComment.objects.all()))
        comments = dict(((c.id, c) for c in Comment.objects.all() if c.id not in hcomments))

        cursor = connection.cursor()

        print len(comments), 'comments found'
        for ix, comment in enumerate(comments.values()):
            print comment.user_name + ': ', repr(comment.comment[:50])
            params = (comment.id, ix+1)
            cursor.execute(sql, params)

        transaction.set_dirty()
