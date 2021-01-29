"""
Flask app for S2ORC pdf2json utility
"""
import hashlib
from flask import Flask, request, jsonify, flash, url_for, redirect, render_template, send_file
from pdf2json.process_pdf import process_stream

app = Flask(__name__)

ALLOWED_EXTENSIONS = {'pdf'}


@app.route('/')
def home():
    return render_template("home.html")

@app.route('/', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        filename = uploaded_file.filename
        # read file
        pdf_stream = uploaded_file.stream
        pdf_content = pdf_stream.read()
        # compute hash
        pdf_sha = hashlib.sha1(pdf_content).hexdigest()
        # get results
        results = process_stream(filename, pdf_sha, pdf_content)
        return jsonify(results)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
