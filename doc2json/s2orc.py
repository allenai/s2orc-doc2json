"""
S2ORC classes
"""

from datetime import datetime
from typing import Dict, List, Optional
from doc2json.config import *


CORRECT_KEYS = {
    "issn": "issue",
    "type": "type_str"
}

SKIP_KEYS = {
    'link',
    'bib_id'
}

REFERENCE_OUTPUT_KEYS = {
    'figure': {'text', 'type_str', 'uris', 'num'},
    'table': {'text', 'type_str', 'content', 'num', 'html'},
    'footnote': {'text', 'type_str', 'num'},
    'section': {'text', 'type_str', 'num', 'parent'},
    'equation': {'text', 'type_str', 'latex', 'mathml', 'num'}
}

METADATA_KEYS = {
    "title", "authors", "year", "venue", "identifiers"
}


class ReferenceEntry:
    """
    Class for representing S2ORC figure and table references

    An example json representation (values are examples, not accurate):

    {
      "FIGREF0": {
        "text": "FIG. 2. Depth profiles of...",
        "latex": null,
        "type": "figure"
      },
      "TABREF2": {
        "text": "Diversity indices of...",
        "latex": null,
        "type": "table",
        "content": "",
        "html": ""
      }
    }
    """
    def __init__(
            self,
            ref_id: str,
            text: str,
            type_str: str,
            latex: Optional[str] = None,
            mathml: Optional[str] = None,
            content: Optional[str] = None,
            html: Optional[str] = None,
            uris: Optional[List[str]] = None,
            num: Optional[str] = None,
            parent: Optional[str] = None
    ):
        self.ref_id = ref_id
        self.text = text
        self.type_str = type_str
        self.latex = latex
        self.mathml = mathml
        self.content = content
        self.html = html
        self.uris = uris
        self.num = num
        self.parent = parent

    def as_json(self):
        keep_keys = REFERENCE_OUTPUT_KEYS.get(self.type_str, None)
        if keep_keys:
            return {
                k: self.__getattribute__(k) for k in keep_keys
            }
        else:
            return {
                "text": self.text,
                "type": self.type_str,
                "latex": self.latex,
                "mathml": self.mathml,
                "content": self.content,
                "html": self.html,
                "uris": self.uris,
                "num": self.num,
                "parent": self.parent
            }


class BibliographyEntry:
    """
    Class for representing S2ORC parsed bibliography entries

    An example json representation (values are examples, not accurate):

    {
        "title": "Mobility Reports...",
        "authors": [
            {
                "first": "A",
                "middle": ["A"],
                "last": "Haija",
                "suffix": ""
            }
        ],
        "year": 2015,
        "venue": "IEEE Wireless Commun. Mag",
        "volume": "42",
        "issn": "9",
        "pages": "80--92",
        "other_ids": {
            "doi": [
                "10.1109/TWC.2014.2360196"
            ],

        }
    }

    """
    def __init__(
            self,
            bib_id: str,
            title: str,
            authors: List[Dict[str, str]],
            ref_id: Optional[str] = None,
            year: Optional[int] = None,
            venue: Optional[str] = None,
            volume: Optional[str] = None,
            issue: Optional[str] = None,
            pages: Optional[str] = None,
            other_ids: Dict[str, List] = None,
            num: Optional[int] = None,
            urls: Optional[List] = None,
            raw_text: Optional[str] = None,
            links: Optional[List] = None
    ):
        self.bib_id = bib_id
        self.ref_id = ref_id
        self.title = title
        self.authors = authors
        self.year = year
        self.venue = venue
        self.volume = volume
        self.issue = issue
        self.pages = pages
        self.other_ids = other_ids
        self.num = num
        self.urls = urls
        self.raw_text = raw_text
        self.links = links

    def as_json(self):
        return {
            "ref_id": self.ref_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "other_ids": self.other_ids,
            "num": self.num,
            "urls": self.urls,
            "raw_text": self.raw_text,
            "links": self.links
        }


class Affiliation:
    """
    Class for representing affiliation info

    Example:
        {
            "laboratory": "Key Laboratory of Urban Environment and Health",
            "institution": "Chinese Academy of Sciences",
            "location": {
              "postCode": "361021",
              "settlement": "Xiamen",
              "country": "People's Republic of China"
        }
    """
    def __init__(
            self,
            laboratory: str,
            institution: str,
            location: Dict
    ):
        self.laboratory = laboratory
        self.institution = institution
        self.location = location

    def as_json(self):
        return {
            "laboratory": self.laboratory,
            "institution": self.institution,
            "location": self.location
        }


class Author:
    """
    Class for representing paper authors

    Example:

        {
          "first": "Anyi",
          "middle": [],
          "last": "Hu",
          "suffix": "",
          "affiliation": {
            "laboratory": "Key Laboratory of Urban Environment and Health",
            "institution": "Chinese Academy of Sciences",
            "location": {
              "postCode": "361021",
              "settlement": "Xiamen",
              "country": "People's Republic of China"
            }
          },
          "email": ""
        }
    """
    def __init__(
            self,
            first: str,
            middle: List[str],
            last: str,
            suffix: str,
            affiliation: Optional[Dict] = None,
            email: Optional[str] = None
    ):
        self.first = first
        self.middle = middle
        self.last = last
        self.suffix = suffix
        self.affiliation = Affiliation(**affiliation) if affiliation else {}
        self.email = email

    def as_json(self):
        return {
            "first": self.first,
            "middle": self.middle,
            "last": self.last,
            "suffix": self.suffix,
            "affiliation": self.affiliation.as_json() if self.affiliation else {},
            "email": self.email
        }


class Metadata:
    """
    Class for representing paper metadata

    Example:
    {
      "title": "Niche Partitioning...",
      "authors": [
        {
          "first": "Anyi",
          "middle": [],
          "last": "Hu",
          "suffix": "",
          "affiliation": {
            "laboratory": "Key Laboratory of Urban Environment and Health",
            "institution": "Chinese Academy of Sciences",
            "location": {
              "postCode": "361021",
              "settlement": "Xiamen",
              "country": "People's Republic of China"
            }
          },
          "email": ""
        }
      ],
      "year": "2011-11"
    }
    """
    def __init__(
            self,
            title: str,
            authors: List[Dict],
            year: Optional[str] = None,
            venue: Optional[str] = None,
            identifiers: Optional[Dict] = {}
    ):
        self.title = title
        self.authors = [Author(**author) for author in authors]
        self.year = year
        self.venue = venue
        self.identifiers = identifiers

    def as_json(self):
        return {
            "title": self.title,
            "authors": [author.as_json() for author in self.authors],
            "year": self.year,
            "venue": self.venue,
            "identifiers": self.identifiers
        }


class Paragraph:
    """
    Class for representing a parsed paragraph from Grobid xml
    All xml tags are removed from the paragraph text, all figures, equations, and tables are replaced
    with a special token that maps to a reference identifier
    Citation mention spans and section header are extracted

    An example json representation (values are examples, not accurate):

    {
        "text": "Formal language techniques BID1 may be used to study FORMULA0 (see REF0)...",
        "mention_spans": [
            {
                "start": 27,
                "end": 31,
                "text": "[1]")
        ],
        "ref_spans": [
            {
                "start": ,
                "end": ,
                "text": "Fig. 1"
            }
        ],
        "eq_spans": [
            {
                "start": 53,
                "end": 61,
                "text": "α = 1",
                "latex": "\\alpha = 1",
                "ref_id": null
            }
        ],
        "section": "Abstract"
    }
    """
    def __init__(
            self,
            text: str,
            cite_spans: List[Dict],
            ref_spans: List[Dict],
            eq_spans: Optional[List[Dict]] = [],
            section: Optional = None,
            sec_num: Optional = None
    ):
        self.text = text
        self.cite_spans = cite_spans
        self.ref_spans = ref_spans
        self.eq_spans = eq_spans
        if type(section) == str:
            if section:
                sec_parts = section.split('::')
                section_list = [[None, sec_name] for sec_name in sec_parts]
            else:
                section_list = None
            if section_list and sec_num:
                section_list[-1][0] = sec_num
        else:
            section_list = section
        self.section = section_list

    def as_json(self):
        return {
            "text": self.text,
            "cite_spans": self.cite_spans,
            "ref_spans": self.ref_spans,
            "eq_spans": self.eq_spans,
            "section": '::'.join([sec[1] for sec in self.section]) if self.section else "",
            "sec_num": self.section[-1][0] if self.section else None
        }


class Paper:
    """
    Class for representing a parsed S2ORC paper
    """
    def __init__(
            self,
            paper_id: str,
            pdf_hash: str,
            metadata: Dict,
            abstract: List[Dict],
            body_text: List[Dict],
            back_matter: List[Dict],
            bib_entries: Dict,
            ref_entries: Dict
        ):
        self.paper_id = paper_id
        self.pdf_hash = pdf_hash
        self.metadata = Metadata(**metadata)
        self.abstract = [Paragraph(**para) for para in abstract]
        self.body_text = [Paragraph(**para) for para in body_text]
        self.back_matter = [Paragraph(**para) for para in back_matter]
        self.bib_entries = [
            BibliographyEntry(
                bib_id=key,
                **{CORRECT_KEYS[k] if k in CORRECT_KEYS else k: v for k, v in bib.items() if k not in SKIP_KEYS}
            ) for key, bib in bib_entries.items()
        ]
        self.ref_entries = [
            ReferenceEntry(
                ref_id=key,
                **{CORRECT_KEYS[k] if k in CORRECT_KEYS else k: v for k, v in ref.items() if k != 'ref_id'}
            ) for key, ref in ref_entries.items()
        ]

    def as_json(self):
        return {
            "paper_id": self.paper_id,
            "pdf_hash": self.pdf_hash,
            "metadata": self.metadata.as_json(),
            "abstract": [para.as_json() for para in self.abstract],
            "body_text": [para.as_json() for para in self.body_text],
            "back_matter": [para.as_json() for para in self.back_matter],
            "bib_entries": {bib.bib_id: bib.as_json() for bib in self.bib_entries},
            "ref_entries": {ref.ref_id: ref.as_json() for ref in self.ref_entries}
        }

    @property
    def raw_abstract_text(self) -> str:
        """
        Get all the body text joined by a newline
        :return:
        """
        return '\n'.join([para.text for para in self.abstract])

    @property
    def raw_body_text(self) -> str:
        """
        Get all the body text joined by a newline
        :return:
        """
        return '\n'.join([para.text for para in self.body_text])

    def release_json(self, doc_type: str="pdf"):
        """
        Return in release JSON format
        :return:
        """
        # TODO: not fully implemented; metadata format is not right; extra keys in some places
        release_dict = {"paper_id": self.paper_id}
        release_dict.update({"header": {
            "generated_with": f'{S2ORC_NAME_STRING} {S2ORC_VERSION_STRING}',
            "date_generated": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }})
        release_dict.update(self.metadata.as_json())
        release_dict.update({"abstract": self.raw_abstract_text})
        release_dict.update({
            f"{doc_type}_parse": {
                "paper_id": self.paper_id,
                "_pdf_hash": self.pdf_hash,
                "abstract": [para.as_json() for para in self.abstract],
                "body_text": [para.as_json() for para in self.body_text],
                "back_matter": [para.as_json() for para in self.back_matter],
                "bib_entries": {bib.bib_id: bib.as_json() for bib in self.bib_entries},
                "ref_entries": {ref.ref_id: ref.as_json() for ref in self.ref_entries}
            }
        })
        return release_dict


def load_s2orc(paper_dict: Dict) -> Paper:
    """
    Load release S2ORC into Paper class
    :param paper_dict:
    :return:
    """
    paper_id = paper_dict['paper_id']
    pdf_hash = paper_dict.get('_pdf_hash', paper_dict.get('s2_pdf_hash', None))

    # 2019 gorc parses
    if "grobid_parse" in paper_dict and paper_dict.get("grobid_parse"):
        metadata = {k: v for k, v in paper_dict["metadata"].items() if k in METADATA_KEYS}
        abstract = paper_dict.get("grobid_parse").get("abstract", [])
        body_text = paper_dict.get("grobid_parse").get("body_text", [])
        back_matter = paper_dict.get("grobid_parse").get("back_matter", [])
        bib_entries = paper_dict.get("grobid_parse").get("bib_entries", {})
        for k, v in bib_entries.items():
            if 'link' in v:
                v['links'] = [v['link']]
        ref_entries = paper_dict.get("grobid_parse").get("ref_entries", {})
    # current and 2020 s2orc release_json
    elif ("pdf_parse" in paper_dict and paper_dict.get("pdf_parse")) or ("body_text" in paper_dict and paper_dict.get("body_text")):
        if "pdf_parse" in paper_dict:
            paper_dict = paper_dict["pdf_parse"]
        if paper_dict.get("metadata"):
            metadata = {k: v for k, v in paper_dict.get("metadata").items() if k in METADATA_KEYS}
        # 2020 s2orc releases (metadata is separate)
        else:
            metadata = {
                "title": None,
                "authors": [],
                "year": None
            }
        abstract = paper_dict.get("abstract", [])
        body_text = paper_dict.get("body_text", [])
        back_matter = paper_dict.get("back_matter", [])
        bib_entries = paper_dict.get("bib_entries", {})
        for k, v in bib_entries.items():
            if 'link' in v:
                v['links'] = [v['link']]
        ref_entries = paper_dict.get("ref_entries", {})
    else:
        print(paper_id)
        raise NotImplementedError("Unknown S2ORC file type!")

    return Paper(
        paper_id=paper_id,
        pdf_hash=pdf_hash,
        metadata=metadata,
        abstract=abstract,
        body_text=body_text,
        back_matter=back_matter,
        bib_entries=bib_entries,
        ref_entries=ref_entries
    )