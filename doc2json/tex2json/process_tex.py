import os
import json
import argparse
import time

from doc2json.tex2json.tex_to_xml import convert_latex_to_s2orc_json
from doc2json.tex2json.xml_to_json import convert_latex_xml_to_s2orc_json


BASE_TEMP_DIR = 'temp'
BASE_OUTPUT_DIR = 'output'
BASE_LOG_DIR = 'log'

os.makedirs(BASE_TEMP_DIR, exist_ok=True)
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
os.makedirs(BASE_LOG_DIR, exist_ok=True)


def process_tex_file(
        input_file: str,
        temp_dir: str=BASE_TEMP_DIR,
        output_dir: str=BASE_OUTPUT_DIR,
        log_dir: str=BASE_LOG_DIR,
        keep_flag: bool=False,
) -> str:
    """
    Process files in a TEX zip and get JSON representation
    :param input_file:
    :param temp_dir:
    :param output_dir:
    :param log_dir:
    :param keep_flag:
    :return:
    """
    # get paper id as the name of the file
    paper_id = os.path.splitext(input_file)[0].split('/')[-1]
    output_file = os.path.join(output_dir, f'{paper_id}.json')
    cleanup_flag = not keep_flag

    # check if input file exists and output file doesn't
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"{input_file} doesn't exist")
    if os.path.exists(output_file):
        raise Warning(f'{output_file} already exists!')

    # process LaTeX
    xml_file = convert_latex_to_s2orc_json(input_file, temp_dir, cleanup_flag)

    # convert to S2ORC
    paper = convert_latex_xml_to_s2orc_json(xml_file, log_dir)

    # write to file
    with open(output_file, 'w') as outf:
        json.dump(paper.release_json("latex"), outf, indent=4)

    return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run S2ORC TEX2JSON")
    parser.add_argument("-i", "--input", default=None, help="path to the input TEX zip file")
    parser.add_argument("-t", "--temp", default='temp', help="path to a temp dir for partial files")
    parser.add_argument("-o", "--output", default='output', help="path to the output dir for putting json files")
    parser.add_argument("-l", "--log", default='log', help="path to the log dir")
    parser.add_argument("-k", "--keep", default=False, help="keep temporary files")

    args = parser.parse_args()

    input_path = args.input
    temp_path = args.temp
    output_path = args.output
    log_path = args.log
    keep_temp = args.keep

    start_time = time.time()

    os.makedirs(temp_path, exist_ok=True)
    os.makedirs(output_path, exist_ok=True)

    process_tex_dir(input_path, temp_path, output_path, log_path, keep_temp)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    print('done.')
