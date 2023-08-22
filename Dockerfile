FROM python:3.8
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt 
WORKDIR /workspaces/s2orc-pdf2json
COPY ./scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
ENTRYPOINT ["bash", "./scripts/docker-entrypoint.sh" ]