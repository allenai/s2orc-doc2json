FROM openjdk:8u212-jdk

WORKDIR /root/git/s2orc-pdf2json
COPY scripts /root/git/s2orc-pdf2json/scripts
COPY doc2json/grobid2json/grobid/config.yaml /root/git/s2orc-pdf2json/pdf2json/grobid/config.yaml
COPY doc2json/grobid2json/grobid/grobid.properties /root/git/s2orc-pdf2json/pdf2json/grobid/grobid.properties
RUN ./scripts/setup_grobid.sh

ENTRYPOINT [ "./scripts/run_grobid.sh" ]