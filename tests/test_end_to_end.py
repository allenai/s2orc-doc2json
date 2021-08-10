import os
import unittest
import shutil

from doc2json.grobid2json.process_pdf import process_pdf_file
from doc2json.tex2json.process_tex import process_tex_file
from doc2json.jats2json.process_jats import process_jats_file

TEST_PDF_INPUT_DATA = os.path.join('tests', 'pdf')
TEST_PDF_TEMP_DATA = os.path.join('tests', 'pdf_temp')
TEST_PDF_OUTPUT_DATA = os.path.join('tests', 'pdf_output')

TEST_LATEX_INPUT_DATA = os.path.join('tests', 'latex')
TEST_LATEX_TEMP_DIR = os.path.join('tests', 'latex_temp')
TEST_LATEX_EXPAND_DATA = os.path.join(TEST_LATEX_TEMP_DIR, 'latex')
TEST_LATEX_NORM_DATA = os.path.join(TEST_LATEX_TEMP_DIR, 'norm')
TEST_LATEX_XML_DATA = os.path.join(TEST_LATEX_TEMP_DIR, 'xml')
TEST_LATEX_LOG_DATA = os.path.join(TEST_LATEX_TEMP_DIR, 'log')
TEST_LATEX_OUTPUT_DATA = os.path.join('tests', 'latex_output')

TEST_JATS_INPUT_DATA = os.path.join('tests', 'jats')
TEST_JATS_OUTPUT_DATA = os.path.join('tests', 'jats_output')


class TestE2E(unittest.TestCase):

    def test_pdf_e2e(self):
        """
        Check end2end performance (PDF -> JSON)
        :return:
        """
        for fname in os.listdir(TEST_PDF_INPUT_DATA):
            if fname.endswith('.pdf'):
                print(fname)
                # get paper id
                pid = '.'.join(fname.split('.')[:-1])
                # remove output files if previously made
                temp_file_name = os.path.join(TEST_PDF_TEMP_DATA, f'{pid}.tei.xml')
                output_file_name = os.path.join(TEST_PDF_OUTPUT_DATA, f'{pid}.json')
                if os.path.exists(temp_file_name):
                    os.remove(temp_file_name)
                if os.path.exists(output_file_name):
                    os.remove(output_file_name)
                # create directories
                assert os.path.exists(TEST_PDF_INPUT_DATA)
                os.makedirs(TEST_PDF_TEMP_DATA, exist_ok=True)
                os.makedirs(TEST_PDF_OUTPUT_DATA, exist_ok=True)
                # process pdf
                process_pdf_file(
                    os.path.join(TEST_PDF_INPUT_DATA, fname),
                    TEST_PDF_TEMP_DATA,
                    TEST_PDF_OUTPUT_DATA
                )
                # check that output is there
                assert os.path.exists(temp_file_name)
                assert os.path.exists(output_file_name)

    def test_latex_e2e(self):
        """
        Check end2end performance (LaTeX -> JSON)
        :return:
        """
        for fname in os.listdir(TEST_LATEX_INPUT_DATA):
            if fname.endswith('.gz'):
                print(fname)
                # get paper id
                pid = list(os.path.splitext(fname))[0].split('/')[-1]
                # remove output files if previously made
                expand_dir = os.path.join(TEST_LATEX_EXPAND_DATA, pid)
                norm_file_name = os.path.join(TEST_LATEX_NORM_DATA, pid, f'{pid}.tex')
                xml_file_name = os.path.join(TEST_LATEX_XML_DATA, pid, f'{pid}.xml')
                output_file_name = os.path.join(TEST_LATEX_OUTPUT_DATA, f'{pid}.json')
                if os.path.exists(TEST_LATEX_TEMP_DIR):
                    shutil.rmtree(TEST_LATEX_TEMP_DIR)
                if os.path.exists(output_file_name):
                    os.remove(output_file_name)
                # create directories
                assert os.path.exists(TEST_LATEX_INPUT_DATA)
                os.makedirs(TEST_LATEX_TEMP_DIR, exist_ok=True)
                os.makedirs(TEST_LATEX_OUTPUT_DATA, exist_ok=True)
                # process LaTeX
                process_tex_file(
                    os.path.join(TEST_LATEX_INPUT_DATA, fname),
                    temp_dir=TEST_LATEX_TEMP_DIR,
                    output_dir=TEST_LATEX_OUTPUT_DATA,
                    log_dir=TEST_LATEX_LOG_DATA,
                    keep_flag=True
                )
                # check that output is there
                assert os.path.exists(expand_dir)
                assert os.path.exists(norm_file_name)
                assert os.path.exists(xml_file_name)
                assert os.path.exists(output_file_name)

    def test_jats_e2e(self):
        """
        Check end2end performance (JATS -> JSON)
        """
        for fname in os.listdir(TEST_JATS_INPUT_DATA):
            if fname.endswith('nxml'):
                print(fname)
                # get PMC id
                pid = fname.split('/')[-1].split('.')[0]
                # remove output files if exist
                output_file_name = os.path.join(TEST_JATS_OUTPUT_DATA, f'{pid}.json')
                if os.path.exists(output_file_name):
                    os.remove(output_file_name)
                # create directories
                assert os.path.exists(TEST_JATS_INPUT_DATA)
                os.makedirs(TEST_JATS_OUTPUT_DATA, exist_ok=True)
                # process JATS
                process_jats_file(
                    os.path.join(TEST_JATS_INPUT_DATA, fname),
                    output_dir=TEST_JATS_OUTPUT_DATA
                )
                # check that output is there
                assert os.path.exists(output_file_name)
