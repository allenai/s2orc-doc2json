import os
import json
import argparse
import time
from typing import Dict

from doc2json.spp2json.spp.spp_client import SppClient
from doc2json.spp2json.spp.spp_json_to_s2orc_json import convert_spp_json_to_s2orc_json



def process_one_pdf(infile: str, spp_tempfile: str, outfile: str) -> str:

    # process PDF through SPP -> SPP JSON
    client = SppClient()
    client.process(infile, spp_tempfile)

    # process SPP JSON -> S2ORC JSON
    with open(spp_tempfile, 'r') as f_in:
        spp_json = json.load(f_in)
    paper = convert_spp_json_to_s2orc_json(spp_json=spp_json)

    # write to file
    with open(outfile, 'w') as outf:
        json.dump(paper.release_json(), outf, indent=4, sort_keys=False)

    return outfile


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run S2ORC PDF2JSON")
    parser.add_argument("-i", "--indir", default=None, help="path to the input PDF dir")
    parser.add_argument("-t", "--tempdir", default='temp/', help="path to the temp dir for putting SPP JSON files")
    parser.add_argument("-o", "--outdir", default='output/', help="path to the output dir for putting S2ORC JSON files")
    parser.add_argument("-k", "--keep", action='store_true')

    args = parser.parse_args()

    indir = args.indir
    tempdir = args.tempdir
    outdir = args.outdir
    is_keep_temp = args.keep

    os.makedirs(tempdir, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)


    start_time = time.time()

    for fname in os.listdir(indir):
        infile = os.path.join(indir, fname)
        tempfile = os.path.join(tempdir, fname.replace('.pdf', '-spp.json'))
        outfile = os.path.join(outdir, fname.replace('.pdf', '-s2orc.json'))
        process_one_pdf(infile=infile, spp_tempfile=tempfile, outfile=outfile)

        if not is_keep_temp:
            os.remove(tempfile)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    print('done.')
