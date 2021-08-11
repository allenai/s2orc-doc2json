"""
Flask app for S2ORC pdf2json utility
"""
import hashlib
from flask import Flask, request, jsonify, flash, url_for, redirect, render_template, send_file
from doc2json.grobid2json.process_pdf import process_pdf_stream
from doc2json.tex2json.process_tex import process_tex_stream
from doc2json.jats2json.process_jats import process_jats_stream

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'gz', 'nxml'}


@app.route('/')
def home():
    return render_template("home.html")

@app.route('/', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        filename = uploaded_file.filename
        # read pdf file
        if filename.endswith('pdf'):
            pdf_stream = uploaded_file.stream
            pdf_content = pdf_stream.read()
            # compute hash
            pdf_sha = hashlib.sha1(pdf_content).hexdigest()
            # get results
            results = process_pdf_stream(filename, pdf_sha, pdf_content)
            return jsonify(results)
        # read latex file
        elif filename.endswith('gz'):
            zip_stream = uploaded_file.stream
            zip_content = zip_stream.read()
            # get results
            results = process_tex_stream(filename, zip_content)
            return jsonify(results)
        # read nxml file (jats)
        elif filename.endswith('nxml'):
            xml_stream = uploaded_file.stream
            xml_content = xml_stream.read()
            # get results
            results = process_jats_stream(filename, xml_content)
            return jsonify(results)
        # unknown
        else:
            return {
                "Error": "Unknown file type!"
            }

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
