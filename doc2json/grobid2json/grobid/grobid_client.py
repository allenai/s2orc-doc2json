import os
import io
import json
import argparse
import time
import glob
from doc2json.grobid2json.grobid.client import ApiClient
import ntpath
from typing import List

'''
This version uses the standard ProcessPoolExecutor for parallelizing the concurrent calls to the GROBID services.
Given the limits of ThreadPoolExecutor (input stored in memory, blocking Executor.map until the whole input
is acquired), it works with batches of PDF of a size indicated in the config.json file (default is 1000 entries).
We are moving from first batch to the second one only when the first is entirely processed - which means it is
slightly sub-optimal, but should scale better. However acquiring a list of million of files in directories would
require something scalable too, which is not implemented for the moment.
'''

DEFAULT_GROBID_CONFIG = {
    "grobid_server": "localhost",
    "grobid_port": "8070",
    "batch_size": 1000,
    "sleep_time": 5,
    "generateIDs": False,
    "consolidate_header": False,
    "consolidate_citations": False,
    "include_raw_citations": True,
    "include_raw_affiliations": False,
    "max_workers": 2,
}

class GrobidClient(ApiClient):

    def __init__(self, config=None):
        self.config = config or DEFAULT_GROBID_CONFIG
        self.generate_ids = self.config["generateIDs"]
        self.consolidate_header = self.config["consolidate_header"]
        self.consolidate_citations = self.config["consolidate_citations"]
        self.include_raw_citations = self.config["include_raw_citations"]
        self.include_raw_affiliations = self.config["include_raw_affiliations"]
        self.max_workers = self.config["max_workers"]
        self.grobid_server = self.config["grobid_server"]
        self.grobid_port = self.config["grobid_port"]
        self.sleep_time = self.config["sleep_time"]

    def process(self, input: str, output: str, service: str):
        batch_size_pdf = self.config['batch_size']
        pdf_files = []

        for pdf_file in glob.glob(input + "/*.pdf"):
            pdf_files.append(pdf_file)

            if len(pdf_files) == batch_size_pdf:
                self.process_batch(pdf_files, output, service)
                pdf_files = []

        # last batch
        if len(pdf_files) > 0:
            self.process_batch(pdf_files, output, service)

    def process_batch(self, pdf_files: List[str], output: str, service: str) -> None:
        print(len(pdf_files), "PDF files to process")
        for pdf_file in pdf_files:
            self.process_pdf(pdf_file, output, service)

    def process_pdf_stream(self, pdf_file: str, pdf_strm: bytes, output: str, service: str) -> str:
        # process the stream
        files = {
            'input': (
                pdf_file,
                pdf_strm,
                'application/pdf',
                {'Expires': '0'}
            )
        }

        the_url = 'http://' + self.grobid_server
        the_url += ":" + self.grobid_port
        the_url += "/api/" + service

        # set the GROBID parameters
        the_data = {}
        if self.generate_ids:
            the_data['generateIDs'] = '1'
        else:
            the_data['generateIDs'] = '0'

        if self.consolidate_header:
            the_data['consolidateHeader'] = '1'
        else:
            the_data['consolidateHeader'] = '0'

        if self.consolidate_citations:
            the_data['consolidateCitations'] = '1'
        else:
            the_data['consolidateCitations'] = '0'

        if self.include_raw_affiliations:
            the_data['includeRawAffiliations'] = '1'
        else:
            the_data['includeRawAffiliations'] = '0'

        if self.include_raw_citations:
            the_data['includeRawCitations'] = '1'
        else:
            the_data['includeRawCitations'] = '0'

        res, status = self.post(
            url=the_url,
            files=files,
            data=the_data,
            headers={'Accept': 'text/plain'}
        )

        if status == 503:
            time.sleep(self.sleep_time)
            return self.process_pdf_stream(pdf_file, pdf_strm, service)
        elif status != 200:
            with open(os.path.join(output, "failed.log"), "a+") as failed:
                failed.write(pdf_file.strip(".pdf") + "\n")
            print('Processing failed with error ' + str(status))
            return ""
        else:
            return res.text

    def process_pdf(self, pdf_file: str, output: str, service: str) -> None:
        # check if TEI file is already produced
        # we use ntpath here to be sure it will work on Windows too
        pdf_file_name = ntpath.basename(pdf_file)
        filename = os.path.join(output, os.path.splitext(pdf_file_name)[0] + '.tei.xml')
        if os.path.isfile(filename):
            return

        print(pdf_file)
        pdf_strm = open(pdf_file, 'rb').read()
        tei_text = self.process_pdf_stream(pdf_file, pdf_strm, output, service)

        # writing TEI file
        if tei_text:
            with io.open(filename, 'w+', encoding='utf8') as tei_file:
                tei_file.write(tei_text)

    def process_citation(self, bib_string: str, log_file: str) -> str:
        # process citation raw string and return corresponding dict
        the_data = {
            'citations': bib_string,
            'consolidateCitations': '0'
        }

        the_url = 'http://' + self.grobid_server
        the_url += ":" + self.grobid_port
        the_url += "/api/processCitation"

        for _ in range(5):
            try:
                res, status = self.post(
                    url=the_url,
                    data=the_data,
                    headers={'Accept': 'text/plain'}
                )
                if status == 503:
                    time.sleep(self.sleep_time)
                    continue
                elif status != 200:
                    with open(log_file, "a+") as failed:
                        failed.write("-- BIBSTR --\n")
                        failed.write(bib_string + "\n\n")
                    break
                else:
                    return res.text
            except Exception:
                continue

    def process_header_names(self, header_string: str, log_file: str) -> str:
        # process author names from header string
        the_data = {
            'names': header_string
        }

        the_url = 'http://' + self.grobid_server
        the_url += ":" + self.grobid_port
        the_url += "/api/processHeaderNames"

        res, status = self.post(
            url=the_url,
            data=the_data,
            headers={'Accept': 'text/plain'}
        )

        if status == 503:
            time.sleep(self.sleep_time)
            return self.process_header_names(header_string, log_file)
        elif status != 200:
            with open(log_file, "a+") as failed:
                failed.write("-- AUTHOR --\n")
                failed.write(header_string + "\n\n")
        else:
            return res.text

    def process_affiliations(self, aff_string: str, log_file: str) -> str:
        # process affiliation from input string
        the_data = {
            'affiliations': aff_string
        }

        the_url = 'http://' + self.grobid_server
        the_url += ":" + self.grobid_port
        the_url += "/api/processAffiliations"

        res, status = self.post(
            url=the_url,
            data=the_data,
            headers={'Accept': 'text/plain'}
        )

        if status == 503:
            time.sleep(self.sleep_time)
            return self.process_affiliations(aff_string, log_file)
        elif status != 200:
            with open(log_file, "a+") as failed:
                failed.write("-- AFFILIATION --\n")
                failed.write(aff_string + "\n\n")
        else:
            return res.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for GROBID services")
    parser.add_argument("service", help="one of [processFulltextDocument, processHeaderDocument, processReferences]")
    parser.add_argument("--input", default=None, help="path to the directory containing PDF to process")
    parser.add_argument("--output", default=None, help="path to the directory where to put the results")
    parser.add_argument("--config", default=None, help="path to the config file, default is ./config.json")

    args = parser.parse_args()

    input_path = args.input
    config = json.load(open(args.config)) if args.config else DEFAULT_GROBID_CONFIG
    output_path = args.output
    service = args.service

    client = GrobidClient(config=config)

    start_time = time.time()

    client.process(input_path, output_path, service)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
