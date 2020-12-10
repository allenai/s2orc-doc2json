import os
import unittest
from pdf2json.process_pdf import process_pdf_file

TEST_INPUT_DATA = os.path.join('tests', 'input')
TEST_TEMP_DATA = os.path.join('tests', 'temp')
TEST_OUTPUT_DATA = os.path.join('tests', 'output')


class TestOntoEmmaTrainAlign(unittest.TestCase):

    def test_e2e(self):
        """
        Check end2end performance (PDF -> JSON)
        :return:
        """
        for fname in os.listdir(TEST_INPUT_DATA):
            if fname.endswith('.pdf'):
                process_pdf_file(
                    os.path.join(TEST_INPUT_DATA, fname),
                    TEST_TEMP_DATA,
                    TEST_OUTPUT_DATA
                )
                pid = fname.split('.')[0]
                temp_file_name = os.path.join(TEST_TEMP_DATA, f'{pid}.tei.xml')
                output_file_name = os.path.join(TEST_OUTPUT_DATA, f'{pid}.json')
                assert os.path.exists(temp_file_name)
                assert os.path.exists(output_file_name)
