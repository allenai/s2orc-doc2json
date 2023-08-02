#!/bin/bash

# Path to the directory containing PDF files 
DIR=/net/nfs/s2-research/joeh/papers/

# Loop through all PDF files and run command on each
for f in "$DIR"/*.pdf; do
  python doc2json/grobid2json/process_pdf.py -i "$f" -t temp_dir/ -o output_dir/ 
done
