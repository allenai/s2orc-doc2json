import os
import io
import json
import argparse
import time
import glob
import ntpath
from typing import List

import requests

class SppClient:
    def process(self, infile: str, outfile: str):
        with open(infile, 'rb') as f_in:
            files = {"pdf_file": (f_in.name, f_in, "multipart/form-data")}
            r = requests.post('http://localhost:8080/detect', files=files)
            layout = r.json()
            with open(outfile, 'w') as f_out:
                json.dump(layout, f_out, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for ScienceParsePlus (SPP) services")
    parser.add_argument("--input", default=None, help="path to the PDF to process")
    parser.add_argument("--output", default=None, help="path to the target output file")
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    client = SppClient()

    start_time = time.time()

    client.process(input_path, output_path)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
