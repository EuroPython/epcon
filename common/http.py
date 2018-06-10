# coding: utf-8

from django.http import HttpResponse
from weasyprint import HTML


class PdfResponse(HttpResponse):

    def __init__(self, filename, content, **kwargs):
        disposition = 'filename="%s"' % filename
        pdf_content = self.convert_to_pdf(content)
        super(PdfResponse, self).__init__(content=pdf_content, **kwargs)
        self['Content-Type']        = 'application/pdf'
        self['Content-Disposition'] = disposition

        # return response

    def convert_to_pdf(self, content):
        return HTML(string=content).write_pdf()
