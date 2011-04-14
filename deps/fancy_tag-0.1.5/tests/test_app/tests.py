from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase


class FancyTagTestCase(TestCase):
    def testArglessTag(self):
        template = Template('{% load example_tags %}{% say_soup %}')
        self.assertEqual(template.render(Context()), 'Potato Soup')

    def testTagWithArg(self):
        template = Template('{% load example_tags %}{% say_soup "Onion" %}')
        self.assertEqual(template.render(Context()), 'Onion Soup')

    def testTagWithKwarg(self):
        template = Template('{% load example_tags %}{% say_soup type_of_soup="Carrot" %}')
        self.assertEqual(template.render(Context()), 'Carrot Soup')

    def testTagWithKwargAndArg(self):
        template = Template('{% load example_tags %}{% say_soup "Tomato" size="large" %}')
        self.assertEqual(template.render(Context()), 'Tomato Soup (large)')

    def testArgAfterKwargFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup size="large" "Tomato" %}'
                )

    def testArgKwargConflictFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup "Squash" type_of_soup="Leek" %}'
                )

    def testKwargKwargConflictFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup type_of_soup="Squash" type_of_soup="Leek" %}'
                )

    def testTooManyArgs(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup "Barley" "small" "helicopter" %}'
                )

    def testTooFewArgs(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_cheese "Havarty" %}'
                )

    def testMisnamedKwargFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup colour_of_soup="green" %}'
                )

    def testVariableLengthArgs(self):
        template = Template('{% load example_tags %}{% say_names "Ralph" "Jim" "Lou" "Mork" %}')
        self.assertEqual(template.render(Context()), 'Ralph, Jim, Lou, Mork')

    def testVariableLengthKwargs(self):
        template = Template('{% load example_tags %}{% say_languages en="English" fr="French" %}')
        output = template.render(Context())
        self.assertTrue(output == 'en: English, fr: French' or
                output == 'fr: French, en: English')

    def testArgContainingEqualsSign(self):
        template = Template('{% load example_tags %}{% say_names "John :D" "Steve =)" %}')
        self.assertEqual(template.render(Context()), 'John :D, Steve =)')

    def testAsVar(self):
        template = Template('{% load example_tags %}{% say_soup "Beet" as borscht %}I love {{ borscht }}!')
        self.assertEqual(template.render(Context()), 'I love Beet Soup!')

    def testBadAsVarFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_soup "Stone" as "bad var name" %}'
                )

    def testTakesContext(self):
        template = Template('{% load example_tags %}{% say_hello "Hallo" %}')
        self.assertEqual(template.render(Context({'user': 'Tobias'})), 'Hallo, Tobias')

    def testTakesContextOnFuncThatDoesNotTakeContextFails(self):
        self.assertRaises(
                TemplateSyntaxError,
                Template,
                '{% load example_tags %}{% say_hello_like_a_chump "Hallo" %}'
                )
