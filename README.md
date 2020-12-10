# Convert scientific PDFs to S2ORC JSON

This project is a part of [S2ORC](https://github.com/allenai/s2orc). For S2ORC, we convert PDFs to JSON using Grobid and a custom TEI.XML to JSON parser. That TEI.XML to JSON parser is being made available here on its own.

The S2ORC github page includes a JSON schema, but it may be easier to understand that schema based on the python classes in `pdf2json/s2orc.py`.

This custom JSON schema is also used for the [CORD-19](https://github.com/allenai/cord19) project, so those who have interacted with CORD-19 may find this format familiar.

Note: in S2ORC, we also do several other things which are *not* included in this utility:
- Linking bibliography entries to other papers in S2ORC
- Provide LaTeX parses for select arXiv papers

We may eventually make these components available as well, but no promises.

## Setup your environment

NOTE: Miniconda is shown but any other python env manager should be fine

```console
conda create -n s2orc_grobid python=3.8 pytest
source activate s2orc_grobid
pip install -r requirements.txt
python setup.py develop
```

## Install Grobid

You can install your own version of Grobid and get it running, or you can run the following script:

```console
bash scripts/setup_grobid.sh
```

This will start running Grobid immediately. Don't worry if it gets stuck at 88%; this is normal and means Grobid is ready to process PDFs.

The expected port for the Grobid service is 8070, but you can change this as well. Make sure to edit the port in both the Grobid config file as well as `grobid/grobid_client.py`.

## Process a PDF

To process a PDF, try:

```console
python pdf2json/process_pdf.py -i input.pdf -t temp_dir/ -o output_dir/
```

There are a couple of test PDFs in `tests/input/` if you'd like to try with that.

### Contact

Contributions are welcome. Note the embarassingly poor test coverage. Also, please note this pipeline is not perfect. It will miss text or make errors on most PDFs.

Issues: contact `lucyw@allenai.org` or `kylel@allenai.org`

