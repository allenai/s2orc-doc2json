from typing import List, Dict, Optional
import bs4
from bs4 import BeautifulSoup
import re
from collections import defaultdict


SUBSTITUTE_TAGS = {
    'persName',
    'orgName',
    'publicationStmt',
    'titleStmt',
    'biblScope'
}


def clean_tags(el: bs4.element.Tag):
    """
    Replace all tags with lowercase version
    :param el:
    :return:
    """
    for sub_tag in SUBSTITUTE_TAGS:
        for sub_el in el.find_all(sub_tag):
            sub_el.name = sub_tag.lower()


def soup_from_path(file_path: str):
    """
    Read XML file
    :param file_path:
    :return:
    """
    return BeautifulSoup(open(file_path, "rb").read(), "xml")


def get_title_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Returns title
    :return:
    """
    for title_entry in raw_xml.find_all("title"):
        if title_entry.has_attr("level") \
                and title_entry["level"] == "a":
            return title_entry.text
    try:
        return raw_xml.title.text
    except AttributeError:
        return ""


def get_author_names_from_grobid_xml(raw_xml: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Returns a list of dictionaries, one for each author,
    containing the first and last names.

    e.g.
        {
            "first": first,
            "middle": middle,
            "last": last,
            "suffix": suffix
        }
    """
    names = []

    for author in raw_xml.find_all("author"):
        if not author.persname:
            continue

        # forenames include first and middle names
        forenames = author.persname.find_all("forename")

        # surnames include last names
        surnames = author.persname.find_all("surname")

        # name suffixes
        suffixes = author.persname.find_all("suffix")

        first = ""
        middle = []
        last = ""
        suffix = ""

        for forename in forenames:
            if forename["type"] == "first":
                if not first:
                    first = forename.text
                else:
                    middle.append(forename.text)
            elif forename["type"] == "middle":
                middle.append(forename.text)

        if len(surnames) > 1:
            for surname in surnames[:-1]:
                middle.append(surname.text)
            last = surnames[-1].text
        elif len(surnames) == 1:
            last = surnames[0].text

        if len(suffix) >= 1:
            suffix = " ".join([suffix.text for suffix in suffixes])

        names_dict = {
            "first": first,
            "middle": middle,
            "last": last,
            "suffix": suffix
        }

        names.append(names_dict)
    return names


def get_affiliation_from_grobid_xml(raw_xml: BeautifulSoup) -> Dict:
    """
    Get affiliation from grobid xml
    :param raw_xml:
    :return:
    """
    location_dict = dict()
    laboratory_name = ""
    institution_name = ""

    if raw_xml and raw_xml.affiliation:
        for child in raw_xml.affiliation:
            if child.name == "orgname":
                if child.has_attr("type"):
                    if child["type"] == "laboratory":
                        laboratory_name = child.text
                    elif child["type"] == "institution":
                        institution_name = child.text
            elif child.name == "address":
                for grandchild in child:
                    if grandchild.name and grandchild.text:
                        location_dict[grandchild.name] = grandchild.text

        if laboratory_name or institution_name:
            return {
                "laboratory": laboratory_name,
                "institution": institution_name,
                "location": location_dict
            }

    return {}


def get_author_data_from_grobid_xml(raw_xml: BeautifulSoup) -> List[Dict]:
    """
    Returns a list of dictionaries, one for each author,
    containing the first and last names.

    e.g.
        {
            "first": first,
            "middle": middle,
            "last": last,
            "suffix": suffix,
            "affiliation": {
                "laboratory": "",
                "institution": "",
                "location": "",
            },
            "email": ""
        }
    """
    authors = []

    for author in raw_xml.find_all("author"):

        first = ""
        middle = []
        last = ""
        suffix = ""

        if author.persname:
            # forenames include first and middle names
            forenames = author.persname.find_all("forename")

            # surnames include last names
            surnames = author.persname.find_all("surname")

            # name suffixes
            suffixes = author.persname.find_all("suffix")

            for forename in forenames:
                if forename.has_attr("type"):
                    if forename["type"] == "first":
                        if not first:
                            first = forename.text
                        else:
                            middle.append(forename.text)
                    elif forename["type"] == "middle":
                        middle.append(forename.text)

            if len(surnames) > 1:
                for surname in surnames[:-1]:
                    middle.append(surname.text)
                last = surnames[-1].text
            elif len(surnames) == 1:
                last = surnames[0].text

            if len(suffix) >= 1:
                suffix = " ".join([suffix.text for suffix in suffixes])

        affiliation = get_affiliation_from_grobid_xml(author)

        email = ""
        if author.email:
            email = author.email.text

        author_dict = {
            "first": first,
            "middle": middle,
            "last": last,
            "suffix": suffix,
            "affiliation": affiliation,
            "email": email
        }

        authors.append(author_dict)

    return authors


def get_year_from_grobid_xml(raw_xml: BeautifulSoup) -> Optional[int]:
    """
    Returns date published if exists
    :return:
    """
    if raw_xml.date and raw_xml.date.has_attr("when"):
        # match year in date text (which is in some unspecified date format)
        year_match = re.match(r"((19|20)\d{2})", raw_xml.date["when"])
        if year_match:
            year = year_match.group(0)
            if year and year.isnumeric() and len(year) == 4:
                return int(year)
    return None


def get_venue_from_grobid_xml(raw_xml: BeautifulSoup, title_text: str) -> str:
    """
    Returns venue/journal/publisher of bib entry
    Grobid ref documentation: https://grobid.readthedocs.io/en/latest/training/Bibliographical-references/
    level="j": journal title
    level="m": "non journal bibliographical item holding the cited article"
    level="s": series title
    :return:
    """
    title_names = []
    keep_types = ["j", "m", "s"]
    # get all titles of the anove types
    for title_entry in raw_xml.find_all("title"):
        if title_entry.has_attr("level") \
                and title_entry["level"] in keep_types \
                and title_entry.text != title_text:
            title_names.append((title_entry["level"], title_entry.text))
    # return the title name that most likely belongs to the journal or publication venue
    if title_names:
        title_names.sort(key=lambda x: keep_types.index(x[0]))
        return title_names[0][1]
    return ""


def get_volume_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Returns the volume number of grobid bib entry
    Grobid <biblscope unit="volume">
    :return:
    """
    for bibl_entry in raw_xml.find_all("biblscope"):
        if bibl_entry.has_attr("unit") and bibl_entry["unit"] == "volume":
            return bibl_entry.text
    return ""


def get_issue_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Returns the issue number of grobid bib entry
    Grobid <biblscope unit="issue">
    :return:
    """
    for bibl_entry in raw_xml.find_all("biblscope"):
        if bibl_entry.has_attr("unit") and bibl_entry["unit"] == "issue":
            return bibl_entry.text
    return ""


def get_pages_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Returns the page numbers of grobid bib entry
    Grobid <biblscope unit="page">
    :return:
    """
    for bibl_entry in raw_xml.find_all("biblscope"):
        if bibl_entry.has_attr("unit") and bibl_entry["unit"] == "page" and bibl_entry.has_attr("from"):
            from_page = bibl_entry["from"]
            if bibl_entry.has_attr("to"):
                to_page = bibl_entry["to"]
                return f'{from_page}--{to_page}'
            else:
                return from_page
    return ""


def get_other_ids_from_grobid_xml(raw_xml: BeautifulSoup) -> Dict[str, List]:
    """
    Returns a dictionary of other identifiers from grobid bib entry (arxiv, pubmed, doi)
    :param raw_xml:
    :return:
    """
    other_ids = defaultdict(list)

    for idno_entry in raw_xml.find_all("idno"):
        if idno_entry.has_attr("type") and idno_entry.text:
            other_ids[idno_entry["type"]].append(idno_entry.text)

    return other_ids


def get_raw_bib_text_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Returns the raw bibiliography string
    :param raw_xml:
    :return:
    """
    for note in raw_xml.find_all("note"):
        if note.has_attr("type") and note["type"] == "raw_reference":
            return note.text
    return ""


def get_publication_datetime_from_grobid_xml(raw_xml: BeautifulSoup) -> str:
    """
    Finds and returns the publication datetime if it exists
    :param raw_xml:
    :return:
    """
    if raw_xml.publicationStmt:
        for child in raw_xml.publicationstmt:
            if child.name == "date" \
                    and child.has_attr("type") \
                    and child["type"] == "published" \
                    and child.has_attr("when"):
                return child["when"]
    return ""


def parse_bib_entry(bib_entry: BeautifulSoup) -> Dict:
    """
    Parse one bib entry
    :param bib_entry:
    :return:
    """
    clean_tags(bib_entry)
    title = get_title_from_grobid_xml(bib_entry)
    return {
        'ref_id': bib_entry.attrs.get("xml:id", None),
        'title': title,
        'authors': get_author_names_from_grobid_xml(bib_entry),
        'year': get_year_from_grobid_xml(bib_entry),
        'venue': get_venue_from_grobid_xml(bib_entry, title),
        'volume': get_volume_from_grobid_xml(bib_entry),
        'issue': get_issue_from_grobid_xml(bib_entry),
        'pages': get_pages_from_grobid_xml(bib_entry),
        'other_ids': get_other_ids_from_grobid_xml(bib_entry),
        'raw_text': get_raw_bib_text_from_grobid_xml(bib_entry),
        'urls': []
    }


def is_reference_tag(tag: bs4.element.Tag) -> bool:
    return tag.name == "ref" and tag.attrs.get("type", "") == "bibr"


def extract_paper_metadata_from_grobid_xml(tag: bs4.element.Tag) -> Dict:
    """
    Extract paper metadata (title, authors, affiliation, year) from grobid xml
    :param tag:
    :return:
    """
    clean_tags(tag)
    paper_metadata = {
        "title": tag.titlestmt.title.text,
        "authors": get_author_data_from_grobid_xml(tag),
        "year": get_publication_datetime_from_grobid_xml(tag)
    }
    return paper_metadata