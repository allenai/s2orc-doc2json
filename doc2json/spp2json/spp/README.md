# python client for ScienceParsePlus 

### setup

Install [ScienceParsePlus](https://github.com/allenai/scienceparseplus). The README should document how to build and run the service via Docker.  The running service should be accessible at `http://localhost:8080`.


### dependencies

This assumes Python 3.7.

### usage

As a script, run:
```
python spp_client.py --input example.pdf --output example.json
```

As a Python library:
```
import json
from doc2json.spp2json.spp.spp_client import SppClient

client = SppClient()
client.process('example.pdf', 'example.json')

with open('example.json', 'r') as f_in:
    spp_json = json.load(f_in)
```