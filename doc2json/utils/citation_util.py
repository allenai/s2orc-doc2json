# utility functions for handling failure situations with grobid-detected citation spans

import re
from typing import Dict, List, Tuple


BRACKET_REGEX = re.compile(r'\[[1-9]\d{0,2}([,;\-\s]+[1-9]\d{0,2})*;?\]')
BRACKET_STYLE_THRESHOLD = 5

SINGLE_BRACKET_REGEX = re.compile(r'\[([1-9]\d{0,2})\]')
EXPANSION_CHARS = {'-', '–'}


def span_already_added(sub_start: int, sub_end: int, span_indices: List[Tuple[int, int]]) -> bool:
    """
    Check if span is a subspan of existing span
    :param sub_start:
    :param sub_end:
    :param span_indices:
    :return:
    """
    for span_start, span_end in span_indices:
        if sub_start >= span_start and sub_end <= span_end:
            return True
    return False


def is_expansion_string(between_string: str) -> bool:
    """
    Check if the string between two refs is an expansion string
    :param between_string:
    :return:
    """
    if len(between_string) <= 2 \
            and any([c in EXPANSION_CHARS for c in between_string]) \
            and all([c in EXPANSION_CHARS.union({' '}) for c in between_string]):
        return True
    return False


# TODO: still cases like `09bcee03baceb509d4fcf736fa1322cb8adf507f` w/ dups like ['L Jung', 'R Hessler', 'Louis Jung', 'Roland Hessler']
# example paper that has empties & duplicates: `09bce26cc7e825e15a4469e3e78b7a54898bb97f`
def _clean_empty_and_duplicate_authors_from_grobid_parse(authors: List[Dict]) -> List[Dict]:
    """
    Within affiliation, `location` is a dict with fields <settlement>, <region>, <country>, <postCode>, etc.
    Too much hassle, so just take the first one that's not empty.
    """
    # stripping empties
    clean_authors_list = []
    for author in authors:
        clean_first = author['first'].strip()
        clean_last = author['last'].strip()
        clean_middle = [m.strip() for m in author['middle']]
        clean_suffix = author['suffix'].strip()
        if clean_first or clean_last or clean_middle:
            author['first'] = clean_first
            author['last'] = clean_last
            author['middle'] = clean_middle
            author['suffix'] = clean_suffix
            clean_authors_list.append(author)
    # combining duplicates (preserve first occurrence of author name as position)
    key_to_author_blobs = {}
    ordered_keys_by_author_pos = []
    for author in clean_authors_list:
        key = (author['first'], author['last'], ' '.join(author['middle']), author['suffix'])
        if key not in key_to_author_blobs:
            key_to_author_blobs[key] = author
            ordered_keys_by_author_pos.append(key)
        else:
            if author['email']:
                key_to_author_blobs[key]['email'] = author['email']
            if author['affiliation'] and (author['affiliation']['institution'] or author['affiliation']['laboratory'] or author['affiliation']['location']):
                key_to_author_blobs[key]['affiliation'] = author['affiliation']
    dedup_authors_list = [key_to_author_blobs[key] for key in ordered_keys_by_author_pos]
    return dedup_authors_list