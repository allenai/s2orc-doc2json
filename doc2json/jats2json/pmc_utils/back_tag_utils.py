from typing import Dict, List


def _wrap_text(tag):
    return tag.text if tag else ''


def parse_authors(authors_tag) -> List:
    """The PMC XML has a slightly different format than authors listed in front tag."""
    if not authors_tag:
        return []

    authors = []
    for name_tag in authors_tag.find_all('name', recursive=False):
        surname = name_tag.find('surname')
        given_names = name_tag.find('given-names')
        given_names = given_names.text.split(' ') if given_names else None
        suffix = name_tag.find('suffix')
        authors.append({
            'first': given_names[0] if given_names else '',
            'middle': given_names[1:] if given_names else [],
            'last': surname.text if surname else '',
            'suffix': suffix.text if suffix else ''
        })
    return authors


def parse_bib_entries(back_tag) -> Dict:
    bib_entries = {}
    # TODO: PMC2778891 does not have 'ref-list' in its back_tag.  do we even need this, or can directly .find_all('ref')?
    ref_list_tag = back_tag.find('ref-list')
    if ref_list_tag:
        for ref_tag in ref_list_tag.find_all('ref'):
            # The ref ID and label are semantically swapped between CORD-19 and PMC, lol
            ref_label = ref_tag['id']
            ref_id = ref_tag.find('label')
            authors_tag = ref_tag.find('person-group', {'person-group-type': 'author'})
            year = ref_tag.find('year')
            fpage = ref_tag.find('fpage')
            lpage = ref_tag.find('lpage')
            pages = f'{fpage.text}-{lpage.text}' if fpage and lpage else None
            dois = [tag.text for tag in ref_tag.find_all('pub-id', {'pub-id-type': 'doi'})]
            bib_entries[ref_label] = {
                'ref_id': _wrap_text(ref_id),
                'title': _wrap_text(ref_tag.find('article-title')),
                'authors': parse_authors(authors_tag),
                'year': int(year.text) if year and year.text.isdigit() else None,
                'venue': _wrap_text(ref_tag.find('source')),
                'volume': _wrap_text(ref_tag.find('volume')),
                'issn': _wrap_text(ref_tag.find('issue')),
                'pages': pages,
                'other_ids': {
                    'DOI': dois,
                }
            }
    return bib_entries