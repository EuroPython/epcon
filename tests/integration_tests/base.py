class BasePage(object):
    def __init__(self, selenium):
        self.selenium = selenium

    def __getattr__(self, name):
        lookup_data = [lookup for field, lookup in self.fields.iteritems() if name == field][0]

        lookup_method = lookup_data[0]
        lookup_value = lookup_data[1]

        return self.selenium.find_element(lookup_method, lookup_value)

    def open(self):
        return self.selenium.get(self.url)
