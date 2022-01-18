# Convert scientific papers to S2ORC JSON

This project is a part of [S2ORC](https://github.com/allenai/s2orc). For S2ORC, we convert PDFs to JSON using Grobid and a custom TEI.XML to JSON parser. That TEI.XML to JSON parser (`grobid2json`) is made available here. We additionally process LaTeX dumps from arXiv. That parser (`tex2json`) is also made available here.

The S2ORC github page includes a JSON schema, but it may be easier to understand that schema based on the python classes in `doc2json/s2orc.py`.

This custom JSON schema is also used for the [CORD-19](https://github.com/allenai/cord19) project, so those who have interacted with CORD-19 may find this format familiar.

Possible future components (no promises):
- Linking bibliography entries (bibliography consolidation) to papers in S2ORC

## Setup your environment

NOTE: Conda is shown but any other python env manager should be fine

Go [here](https://docs.conda.io/en/latest/miniconda.html) to install the latest version of miniconda.

Then, create an environment:

```console
conda create -n doc2json python=3.8 pytest
conda activate doc2json
pip install -r requirements.txt
python setup.py develop
```

## PDF Processing

The current `grobid2json` tool uses Grobid to first process each PDF into XML, then extracts paper components from the XML.

### Install Grobid

You will need to have Java installed on your machine. Then, you can install your own version of Grobid and get it running, or you can run the following script:

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
python doc2json/grobid2json/process_pdf.py -i tests/pdf/N18-3011.pdf -t temp_dir/ -o output_dir/
```

This will generate a JSON file in the specified `output_dir`. If unspecified, the file will be in the `output/` directory from your path.

## LaTeX Processing

If you want to process LaTeX, you also need to install the following libraries:

- [latexpand](https://ctan.org/pkg/latexpand?lang=en) (`apt install texlive-extra-utils`)
- [tralics](http://www-sop.inria.fr/marelle/tralics/) (`apt install tralics`)

To process LaTeX, all files must be in a zip file, similar to the `*.gz` files you can download from arXiv. 

A few examples are available under `tests/latex/`. For example, you can try:

```console
python doc2json/tex2json/process_tex.py -i test/latex/1911.02782.gz -t temp_dir/ -o output_dir/
```

Again, this will produce a JSON file in the specified `output_dir`.

## PMC JATS XML Processing

To process JATS XML, try:

```console
python doc2json/jats2json/process_jats.py -i test/jats/PMC5828200.nxml -o output_dir/
```

This will create a JSON file with the same paper id in the specified output directory.

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
curl localhost:8080/ -F file=@tests/pdf/N18-3011.pdf
```

## Citation

If you use this utility in your research, please cite:

```
@inproceedings{lo-wang-2020-s2orc,
    title = "{S}2{ORC}: The Semantic Scholar Open Research Corpus",
    author = "Lo, Kyle  and Wang, Lucy Lu  and Neumann, Mark  and Kinney, Rodney  and Weld, Daniel",
    booktitle = "Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics",
    month = jul,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.acl-main.447",
    doi = "10.18653/v1/2020.acl-main.447",
    pages = "4969--4983"
}
```

## Contact

Contributions are welcome. Note the embarassingly poor test coverage. Also, please note this pipeline is not perfect. It will miss text or make errors on most PDFs. The current PDF to JSON step uses Grobid; we may replace this with a different model in the future.

Issues: contact `lucyw@allenai.org` or `kylel@allenai.org`

