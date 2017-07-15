from django.core.urlresolvers import reverse
from django.test import TestCase


class ResetPasswordTestCase(TestCase):
    def test_reset_password(self):
        url = reverse('password_reset_confirm',
                      kwargs={
                          'uidb64': '12123313A',
                          'token': 'a0-1212dd'
                      })

        response = self.client.get(url)

        self.assertTemplateUsed(response, 'registration/password_reset_confirm.html')