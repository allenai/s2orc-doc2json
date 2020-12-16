import os
import requests
import pandas as pd
import json
import boto3
import tqdm

from pys2 import pys2

from pdf2json.process_pdf import process_pdf_file


ES_API = 'http://es5.cf.development.s2.dev.ai2.in:9200/figureextraction/figureExtraction/'

S3_BUCKET = 'ai2-s2-scia11y'
S3_PREFIX = 'adhoc'


def get_alt_shas(corpus_id):
    query = '''
        SELECT
            corpus_paper_id,
            paper_sha
        FROM content.papers
        WHERE corpus_paper_id=%s
        LIMIT 10
        ''' %(corpus_id)
    res = pd.read_sql(query, pys2._get_redshift_connection())
    return list(res['paper_sha'])


# Queries deepfigures api
def get_figures_and_tables(pdf_parse):
    if pdf_parse['_pdf_hash']:
        pdf_shas = [pdf_parse['_pdf_hash']] + get_alt_shas(pdf_parse['paper_id'])
    else:
        pdf_shas = get_alt_shas(pdf_parse['paper_id'])
    if not pdf_shas:
        raise Exception(f"No SHA for corpus ID: {pdf_parse['paper_id']}")
    responses = []
    max_ft = 0
    max_i = 0
    for i, pdf_sha in enumerate(pdf_shas):
        response = requests.get(ES_API + pdf_sha).json()
        ft = {"figure":[],
                "table": []}
        if "_source" in response:
            if "figures" in response["_source"]:
                for item in response["_source"]["figures"]:
                    if ':' in item['caption']:
                        item['name'], item['caption'] = item['caption'].split(':', 1)
                    else:
                        item['name'] = ''
                    ft[item['figureType']].append(item)
        responses.append(ft)
        if (len(ft['figure']) + len(ft['table'])) > max_ft:
            max_ft = (len(ft['figure']) + len(ft['table']))
            max_i = i
    return responses[max_i]


if __name__ == '__main__':

    # process pdfs
    out_files = []
    os.makedirs('temp', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    for pdf_file in tqdm.tqdm(os.listdir('pdfs')):
        out_file = os.path.join('output', f"{pdf_file.split('.')[0]}.json")
        if os.path.exists(out_file):
            print(f'skipping {pdf_file}')
            continue
        if pdf_file.endswith('.pdf'):
            out_file = process_pdf_file(os.path.join('pdfs', pdf_file), 'temp', 'output')
            out_files.append(out_file)

    # get deepfigs info
    fig_dir = 'figs'
    os.makedirs(fig_dir, exist_ok=True)
    for out_file in tqdm.tqdm(os.listdir('output')):
        fig_file = os.path.join(fig_dir, out_file)
        with open(os.path.join('output', out_file), 'r') as f:
            contents = json.load(f)
        fig_tabs = get_figures_and_tables(contents['pdf_parse'])
        contents['deepfigures_extractions'] = fig_tabs
        contents['deepfigures_same_pdf'] = None
        with open(fig_file, 'w') as outf:
            json.dump(contents, outf)

    # upload to s3
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET)
    num_files = 0
    for fig_file in os.listdir(fig_dir):
        file_path = os.path.join(fig_dir, fig_file)
        prefix_for_upload = os.path.join(S3_PREFIX, fig_file)
        bucket.upload_file(file_path, prefix_for_upload)
        num_files += 1

    print(f'{num_files} files uploaded')
    print('done.')




