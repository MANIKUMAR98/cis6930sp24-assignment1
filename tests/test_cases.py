import unittest, sys, argparse, os
from io import StringIO
from censoror import (censor_using_google_nlp, load_google_nlp_cred, censor_using_spacy, load_spacy,
                      censor_address_using_pyap, write_data_to_stats, process_file)


def initialize_statistics():
    statistics = {}
    file_statistics = {
        'names': 0,
        'addresses': 0,
        'dates': 0,
        'phone_numbers': 0,
    }
    statistics['test_file'] = file_statistics
    return statistics


class TestCensorUsingGoogleNLP(unittest.TestCase):

    def test_censor_using_google_nlp(self):
        load_google_nlp_cred()
        input_text = "Manikumar lives at Main St. His phone number is (352) 555-1234. He was born on 01/01/1990."
        expected_output = "█████████ lives at ████████ His phone number is ██████████████. He was born on ██████████."
        statistics = initialize_statistics()
        result = censor_using_google_nlp(input_text, 'test_file', statistics, input_text)
        self.assertEqual(result, expected_output)

    def test_censor_using_spacy(self):
        nlp = load_spacy()
        text = "My name is Manikumar"
        expected_output = "My name is █████████"
        statistics = initialize_statistics()
        result = censor_using_spacy(text, nlp, 'test_file', statistics, text)
        self.assertEqual(result, expected_output)

    def test_censor_address_using_pyap(self):
        text = "I stay at 2525 SW 39th Blvd Chicago Illinois 50368"
        expected = "I stay at ████████████████████████████████████████"
        result = censor_address_using_pyap(text, 'test_file', initialize_statistics(), text)
        self.assertEqual(result, expected)

    def test_write_data_to_stats_stderr(self):
        captured_output = StringIO()
        sys.stderr = captured_output

        statistics = {
            'test_file': {'names': 1, 'addresses': 2, 'dates': 3, 'phone_numbers': 4}
        }
        file_count = 1
        stats = "stderr"

        write_data_to_stats(stats, file_count, statistics)

        captured_output_value = captured_output.getvalue()

        sys.stderr = sys.__stderr__
        expected_output = (
            "Censoring Statistics:\n"
            "--------------------------\n"
            "Total Files Processed: 1\n"
            "---------------------\n"
            "File Name: test_file\n"
            "- Censored types and count: \n"
            " - Names: 1\n"
            " - Addresses: 2\n"
            " - Dates: 3\n"
            " - Phone_numbers: 4\n"
            "--------------------------\n"
        )
        self.assertEqual(captured_output_value, expected_output)

    def test_process_file_creates_output_file(self):
        if os.path.exists("tests/test_file.txt.censored"):
            os.remove("tests/test_file.txt.censored")
        input_file = 'tests/test_file.txt'
        args = argparse.Namespace(
            input=[input_file],
            names=True,
            dates=True,
            phones=True,
            address=True,
            output='tests/',
            stats='stdout'
        )
        nlp = load_spacy()
        load_google_nlp_cred()
        actual_file_name = 'test_file'
        statistics = initialize_statistics()
        process_file(input_file, args, nlp, actual_file_name, statistics)
        expected_output_file = os.path.join(args.output, 'test_file.txt.censored')
        self.assertTrue(os.path.exists(expected_output_file))


if __name__ == '__main__':
    unittest.main()
