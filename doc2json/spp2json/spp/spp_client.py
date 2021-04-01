import os
import io
import json
import argparse
import time
import glob
import ntpath
from typing import List


class SppClient:
    def process(self, input: str, output: str):
        raise NotImplementedError


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for ScienceParsePlus (SPP) services")
    parser.add_argument("--input", default=None, help="path to the directory containing PDF to process")
    parser.add_argument("--output", default=None, help="path to the directory where to put the results")
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    client = SppClient()

    start_time = time.time()

    client.process(input_path, output_path)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
