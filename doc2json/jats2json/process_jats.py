import os
import json
import argparse
import time
from typing import Optional

from doc2json.jats2json.jats_to_json import convert_jats_xml_to_s2orc_json


BASE_TEMP_DIR = 'temp'
BASE_OUTPUT_DIR = 'output'
BASE_LOG_DIR = 'log'


def process_jats_stream(
        fname: str,
        stream: bytes,
        temp_dir: str=BASE_TEMP_DIR
):
    """
    Process a jats file stream
    :param fname:
    :param stream:
    :param temp_dir:
    :return:
    """
    temp_input_dir = os.path.join(temp_dir, 'input')
    temp_input_file = os.path.join(temp_input_dir, fname)

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(temp_input_dir, exist_ok=True)

    with open(temp_input_file, 'wb') as outf:
        outf.write(stream)

    output_file = process_jats_file(temp_input_file)

    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            contents = json.load(f)
            return contents
    else:
        return []


def process_jats_file(
        jats_file: str,
        output_dir: str=BASE_OUTPUT_DIR,
        log_dir: str=BASE_LOG_DIR,
) -> Optional[str]:
    """
    Process files in a JATS XML file and get JSON representation
    :param jats_file:
    :param output_dir:
    :param log_dir:
    :return:
    """
    # create directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # get paper id as the name of the file
    paper_id = os.path.splitext(jats_file)[0].split('/')[-1]
    output_file = os.path.join(output_dir, f'{paper_id}.json')

    # check if input file exists and output file doesn't
    if not os.path.exists(jats_file):
        raise FileNotFoundError(f"{jats_file} doesn't exist")
    if os.path.exists(output_file):
        print(f'{output_file} already exists!')

    # convert to S2ORC
    paper = convert_jats_xml_to_s2orc_json(jats_file, log_dir)

    # write to file
    with open(output_file, 'w') as outf:
        json.dump(paper.release_json("jats"), outf, indent=4, sort_keys=False)

    return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run S2ORC JATS2JSON")
    parser.add_argument("-i", "--input", default=None, help="path to the input JATS XML file")
    parser.add_argument("-o", "--output", default='output', help="path to the output dir for putting json files")
    parser.add_argument("-l", "--log", default='log', help="path to the log dir")
    parser.add_argument("-k", "--keep", default=False, help="keep temporary files")

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    log_path = args.log
    keep_temp = args.keep

    start_time = time.time()

    os.makedirs(output_path, exist_ok=True)

    process_jats_file(input_path, output_path, log_path, keep_temp)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    print('done.')
