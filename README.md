# Convert scientific papers to S2ORC JSON

This project is a part of [S2ORC](https://github.com/allenai/s2orc). For S2ORC, we convert PDFs to JSON using Grobid and a custom TEI.XML to JSON parser. That TEI.XML to JSON parser (`pdf2json`) is made available here. We additionally process LaTeX dumps from arXiv. That parser (`tex2json`) is also made available here.

The S2ORC github page includes a JSON schema, but it may be easier to understand that schema based on the python classes in `doc2json/s2orc.py`.

This custom JSON schema is also used for the [CORD-19](https://github.com/allenai/cord19) project, so those who have interacted with CORD-19 may find this format familiar.

Note: in S2ORC and CORD-19, we also do several other things which are *not* included in this utility:
- Linking bibliography entries to other papers in S2ORC
- Parse JATS XML files (format used by PubMed Central and others)

We may eventually make these components available as well, but no promises.

## Setup your environment

NOTE: Conda is shown but any other python env manager should be fine

```console
conda create -n doc2json python=3.8 pytest
source activate doc2json
pip install -r requirements.txt
python setup.py develop
```

## PDF Processing

The current `pdf2json` tool uses Grobid to first process each PDF into XML, then extracts paper components from the XML.

### Install Grobid

You can install your own version of Grobid and get it running, or you can run the following script:

```console
bash scripts/setup_grobid.sh
```

This will setup Grobid, currently hard-coded as version 0.6.1. Then run:

```console
bash scripts/run_grobid.sh
```

to start the Grobid server. Don't worry if it gets stuck at 87%; this is normal and means Grobid is ready to process PDFs.

The expected port for the Grobid service is 8070, but you can change this as well. Make sure to edit the port in both the Grobid config file as well as `grobid/grobid_client.py`.

### Process a PDF

There are a couple of test PDFs in `tests/input/` if you'd like to try with that.

For example, you can try:

```console
python doc2json/pdf2json/process_pdf.py -i tests/pdf/b80e338a4e543de6b49cada07156c9149d22.pdf -t temp_dir/ -o output_dir/
```

## LaTeX Processing

To process LaTeX, all files must be in a zip file, similar to the `*.gz` files you can download from arXiv. 

A few examples are available under `tests/latex/`. For example, you can try:

```console
python doc2json/pdf2json/process_tex.py -i test/latex/1911.02782.gz -t temp_dir/ -o output_dir/
```

## Loading a S2ORC JSON file

The format of S2ORC releases have drifted over time. Use the `load_s2orc` function in `doc2json/s2orc.py` to try and load historic and currect S2ORC JSON.

## Run a Flask app and process documents through a web service

To process PDFs, you will first need to start Grobid (defaults to port 8070). If you are processing LaTeX, no need for this step.

```console
bash scripts/run_grobid.sh
```

Then, start the Flask app (defaults to port 8080).

```console
python doc2json/flask/app.py
```

Go to [localhost:8080](localhost:8080) to upload and process papers.

Or alternatively, you can do things like:

```console
curl localhost:8080/ -F file=@tests/input/5cd28c171f9f3b6a8bcebe246159c464980c.pdf
```

## Contact

Contributions are welcome. Note the embarassingly poor test coverage. Also, please note this pipeline is not perfect. It will miss text or make errors on most PDFs. The current PDF to JSON step uses Grobid; we may replace this with a different model in the future.

Issues: contact `lucyw@allenai.org` or `kylel@allenai.org`

