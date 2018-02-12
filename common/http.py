# coding: utf-8

from django.http import HttpResponse


class PdfResponse(HttpResponse):

    def __init__(self, filename, content, **kwargs):

        disposition = 'attachment; filename="%s"' % filename
        pdf_content = self.convert_to_pdf(content)
        response = HttpResponse(
            pdf_content, content_type='application/pdf', **kwargs
        )
        response['Content-Disposition'] = disposition

        return response

    def convert_to_pdf(self, content):
        # TODO(artcz) Implement proper PDF rendering
        raise NotImplementedError
