import os
import json
import argparse
import time

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
        json.dump(paper.as_json(), outf, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run S2ORC PDF2JSON")
    parser.add_argument("-i", "--input_file", default=None, help="path to the input PDF file")
    parser.add_argument("-t", "--temp", default='temp/', help="path to the temp dir for putting tei xml files")
    parser.add_argument("-o", "--output", default='output/', help="path to the output dir for putting json files")
    parser.add_argument("-k", "--keep", action='store_true')

    args = parser.parse_args()

    input_path = args.input
    temp_path = args.temp
    output_path = args.output
    keep_temp = args.keep

    start_time = time.time()

    os.makedirs(temp_path, exist_ok=True)
    os.makedirs(output_path, exist_ok=True)

    process_pdf_file(input_path, temp_path, output_path)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    print('done.')