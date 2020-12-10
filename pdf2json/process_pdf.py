import os
import json

from grobid.grobid_client import GrobidClient
from pdf2json.tei_to_json import convert_tei_xml_file_to_s2orc_json


def process_pdf_file(input_file: str, temp_dir: str, output_dir: str):
    """
    Process a PDF file and get JSON representation
    :param input_file:
    :param temp_dir:
    :param output_dir:
    :return:
    """
    # get paper id as the name of the file
    paper_id = input_file.split('/')[-1].split('.')[0]
    tei_file = os.path.join(temp_dir, f'{paper_id}.tei.xml')
    output_file = os.path.join(output_dir, f'{paper_id}.json')

    # check if input file exists and output file doesn't
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"{input_file} doesn't exist")
    if os.path.exists(output_file):
        raise FileExistsError(f'{output_file} already exists!')

    # process PDF through Grobid -> TEI.XML
    client = GrobidClient()
    client.process_pdf(input_file, temp_dir, "processFulltextDocument")

    # process TEI.XML -> JSON
    assert os.path.exists(tei_file)
    paper = convert_tei_xml_file_to_s2orc_json(tei_file)

    # write to file
    with open(output_file, 'w') as outf:
        json.dump(paper.as_json(), outf)


