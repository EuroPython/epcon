from django.core.urlresolvers import reverse

from tests.integration_tests.base import BasePage

from selenium.webdriver.common.by import By


class RegistrationPage(BasePage):
    fields = {
        'first_name': (By.ID, 'id_first_name'),
        'last_name': (By.ID, 'id_last_name'),
        'email': (By.ID, 'id_email'),
        'password1': (By.ID, 'id_password1'),
        'password2': (By.ID, 'id_password2'),
        'form': (By.XPATH, '/html/body/div[1]/div/section/div/div[2]/div/form/fieldset[2]/button')
    }

    def __init__(self, base_url, *args, **kwargs):
        super(RegistrationPage, self).__init__(*args, **kwargs)
        self.url = base_url + reverse('assopy-new-account')
