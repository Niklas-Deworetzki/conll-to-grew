"""
End-to-End test for the translator.

Test cases are defined in test_cases.
"""

import unittest
from pathlib import Path

from conll2grew import conll_to_grew


class TranslatorTests(unittest.TestCase):
    pass


def generate_test_case(defined_input: str, expected_output: str):
    def test_case(self):
        actual_output = conll_to_grew(defined_input)
        self.assertEqual(actual_output, expected_output)

    return test_case


def report_malformed_test_case(case: str, exception: Exception):
    def test_case(self):
        self.fail(f'Malformed test case {case}: {exception}')

    return test_case


def import_test_cases():
    definitions = Path(__file__).parent / 'test_cases'

    for definition in definitions.iterdir():
        input_file = definition / 'conllu'
        output_file = definition / 'grew'

        try:
            with input_file.open('r') as defined_input, output_file.open('r') as expected_output:
                test_case = generate_test_case(defined_input.read(), expected_output.read())
        except Exception as ex:
            test_case = report_malformed_test_case(definition.stem, ex)

        setattr(TranslatorTests, f'test_{definition.stem}', test_case)


import_test_cases()
