#!/usr/bin/env bash

# put in your doc2json directory here
export DOC2JSON_HOME=$HOME/s2orc-doc2json

# Download Grobid
cd $HOME
wget https://github.com/kermitt2/grobid/archive/0.7.3.zip
unzip 0.7.3.zip
rm 0.7.3.zip
cd $HOME/grobid-0.7.3
./gradlew clean install

## Grobid configurations
# increase max.connections to slightly more than number of processes
# decrease logging level
# this isn't necessary but is nice to have if you are processing lots of files
cp $DOC2JSON_HOME/doc2json/grobid/config.yaml $HOME/grobid-0.7.3/grobid-service/config/config.yaml
cp $DOC2JSON_HOME/doc2json/grobid/grobid.properties $HOME/grobid-0.7.3/grobid-home/config/grobid.properties

## Start Grobid
./gradlew run
