import factory


class MessageFactory(object):
    subject = factory.Faker('sentence', nb_words=6, variable_nb_words=True, ext_word_list=None)
    message = factory.Faker('paragraph', nb_sentences=3, variable_nb_sentences=True, ext_word_list=None)