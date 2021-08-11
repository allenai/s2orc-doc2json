"""
Mostly copied from cite2vec paper_parsing.parse_nxml
"""

from typing import List, Set, Dict, Callable

import os
import json
import re
import multiprocessing
from bs4 import BeautifulSoup
from tqdm import tqdm
from glob import glob
from pprint import pprint

from doc2json.utils.soup_utils import destroy_unimportant_tags_inplace
from doc2json.jats2json.pmc_utils.front_tag_utils import parse_journal_id_tag, parse_journal_name_tag, \
    parse_title_tag, parse_category_tag, parse_date_tag, parse_doi_tag, parse_pmc_id_tag, parse_pubmed_id_tag, \
    parse_authors, parse_affiliations, parse_abstract_tag, parse_funding_groups, NoAuthorNamesError
from doc2json.jats2json.pmc_utils.extract_utils import extract_fig_blobs, extract_table_blobs, extract_suppl_blobs
from doc2json.jats2json.pmc_utils.all_tag_utils import replace_xref_with_string_placeholders, \
    replace_sup_sub_tags_with_string_placeholders, recurse_parse_section
from doc2json.jats2json.pmc_utils.all_tag_utils import parse_all_paragraphs_in_section
from doc2json.jats2json.pmc_utils.back_tag_utils import parse_bib_entries

from doc2json.s2orc import Paper


def process_front_tag(front_tag, soup) -> Dict:
    # process <journal-meta> tags
    journal_id: str = parse_journal_id_tag(front_tag=front_tag)
    journal_name: str = parse_journal_name_tag(front_tag=front_tag)

    # process <article-meta> tags
    title: str = parse_title_tag(front_tag=front_tag)

    try:
        authors: List[Dict] = parse_authors(front_tag=front_tag)
    except NoAuthorNamesError:
        authors: List[Dict] = []
    affiliations: Dict = parse_affiliations(front_tag=front_tag)

    dates: Dict = parse_date_tag(front_tag=front_tag)

    pubmed_id: str = parse_pubmed_id_tag(front_tag=front_tag)
    pmc_id: str = parse_pmc_id_tag(front_tag=front_tag)
    doi: str = parse_doi_tag(front_tag=front_tag)

    abstract: List[Dict] = parse_abstract_tag(front_tag=front_tag, soup=soup)

    # categories: str = parse_category_tag(front_tag=front_tag)

    funding_groups: List[str] = parse_funding_groups(front_tag=front_tag)

    return {
        'title': title,
        'abstract': abstract,
        'authors': authors,
        'affiliations': affiliations,
        'journal_id': journal_id,
        'journal_name': journal_name,
        'pubmed_id': pubmed_id,
        'pmc_id': pmc_id,
        'doi': doi,
        'year': dates,
        'funding_groups': funding_groups
    }


def process_body_tag(body_tag, soup) -> Dict:
    # replace all xref tags with string placeholders
    replace_xref_with_string_placeholders(soup_tag=body_tag, soup=soup)

    # replace all sup/sub tags with string placeholders
    replace_sup_sub_tags_with_string_placeholders(soup_tag=body_tag, soup=soup)

    # some articles (like PMC2844102) have no sections
    sec_tags = body_tag.find_all('sec', recursive=False)

    # try looking in article tag
    if not sec_tags:
        try:
            sec_tags = body_tag.article.find_all('sec', recursive=False)
        except:
            pass

    if sec_tags:
        all_par_blobs = []
        for sec_tag in sec_tags:
            # note; most sections dont have this 'sec-type' attribute
            if sec_tag.get('sec-type') == 'supplementary-material':
                # hopefully all the important supplementary content already extracted above in previous step
                continue
            else:
                par_blobs = recurse_parse_section(sec_tag=sec_tag)
                all_par_blobs.extend(par_blobs)
    else:
        all_par_blobs = parse_all_paragraphs_in_section(body_tag)

    return {
        'body_text': all_par_blobs,
    }


def process_back_tag(back_tag) -> Dict:
    # glossary = {}
    # if back_tag.find('glossary'):
    #     for def_item_tag in back_tag.find('glossary').find_all('def-item'):
    #         glossary[def_item_tag.find('term').text] = def_item_tag.find('def').text

    # TODO: author contrib and COIs
    # notes = []
    # for notes_tag in back_tag.find_all('notes'):
    #     pass

    # TODO: PMC2778891 has back tag that looks like:  <back><sec><title>Acknowledgements</title><p>Supported by the Austrian Science Fund (P-20670 and W11).</p></sec></back>
    #       that is, it doesn't have 'ack' section.
    acknowledgements: List[Dict] = []
    for ack_tag in back_tag.find_all('ack'):
        title_tag = ack_tag.find('title')
        for par_tag in ack_tag.find_all('p'):
            acknowledgements.append({
                'section': title_tag.text if title_tag is not None else None,
                'text': par_tag.text,
                'funding_sources': [fund_tag.text for fund_tag in par_tag.find_all('funding-source')],
                'urls': [url_tag.text for url_tag in par_tag.find_all('ext-link')]
            })

    bib_entries = parse_bib_entries(back_tag)

    return {
        'acknowledgements': acknowledgements,
        'bib_entries': bib_entries,
    }


def postprocess_front_tags_for_s2orc(init_front_dict: Dict):
    """
    Fix authors and year for S2ORC format
    """
    # Make authors in front tags look like S2ORC
    for a in init_front_dict['authors']:
        a['affiliation'] = {}
        # get affiliation if available
        if a['affiliation_ids']:
            affil_id = a['affiliation_ids'][0]
            affil_text = [affil['text'] for affil in init_front_dict['affiliations'] if affil['id'] == affil_id]
            if affil_text:
                a['affiliation'] = {
                    'laboratory': "",
                    'institution': affil_text[0],
                    'location': {}
                }
        del a['affiliation_ids']
        del a['corresponding']
        del a['orcid']
    del init_front_dict['affiliations']

    # Pick best year and make year int in front tags
    if init_front_dict['year'].get('epub'):
        year = init_front_dict['year'].get('epub')
    elif init_front_dict['year'].get('accepted'):
        year = init_front_dict['year'].get('accepted')
    elif init_front_dict['year'].get('collection'):
        year = init_front_dict['year'].get('collection')
    elif init_front_dict['year'].get('received'):
        year = init_front_dict['year'].get('received')
    else:
        year = None
    init_front_dict['year'] = year

    return init_front_dict


def convert_acks_to_s2orc(paragraphs: List) -> List[Dict]:
    """
    Convert acks to S2ORC paragraphs
    """
    for paragraph_blob in paragraphs:
        paragraph_blob['cite_spans'] = []
        paragraph_blob['ref_spans'] = []
        del paragraph_blob['funding_sources']
        del paragraph_blob['urls']
    return paragraphs


def convert_paragraphs_to_s2orc(paragraphs: List, old_to_new: Dict) -> List[Dict]:
    """
    Convert paragraphs into S2ORC format
    """
    # TODO: temp code to process body text into S2ORC format.  this includes getting rid of sub/superscript spans.
    #       also combining fig & table spans into ref spans.
    #       also remapping the reference / bib labels to the new ones defined earlier in this function.
    #       temporarily, we cant support PMC xml parse bibs, so remove all links to the bibliography (cuz they'll be wrong)
    for paragraph_blob in paragraphs:
        del paragraph_blob['sup_spans']
        del paragraph_blob['sub_spans']
        paragraph_blob['ref_spans'] = []
        for fig_tab_span in paragraph_blob['fig_spans'] + paragraph_blob['table_spans']:
            # replace old ref_id with new ref_id.  default to None if null
            # optional, just wanted to check if this ever happens
            assert fig_tab_span['ref_id']
            fig_tab_span['ref_id'] = old_to_new.get(fig_tab_span['ref_id'])
            paragraph_blob['ref_spans'].append(fig_tab_span)
        del paragraph_blob['fig_spans']
        del paragraph_blob['table_spans']
        for cite_span in paragraph_blob['cite_spans']:
            # replace old cite ids with new cite ids.  again default to None if null
            # optional, just wanted to check if this ever happens
            assert cite_span['ref_id']
            cite_span['ref_id'] = old_to_new.get(cite_span['ref_id'])
    return paragraphs


def convert_jats_xml_to_s2orc_json(jats_file: str, log_dir: str):
    """
    Convert JATS XML to S2ORC JSON
    :param jats_file:
    :param log_dir:
    :return:
    """
    # get file id (PMC id usually)
    file_id = jats_file.split('/')[-1].split('.')[0]

    # read JATS XML
    with open(jats_file, 'r') as f_in:
        soup = BeautifulSoup(f_in, 'lxml')
        destroy_unimportant_tags_inplace(soup, tags_to_remove=['bold', 'italic', 'graphic'])

    # all the XML files have their own wonky reference IDs.  we want to standardize them, but need to remember the old->new mapping
    old_key_to_new_key = {}

    # REFERENCES
    table_blobs = extract_table_blobs(soup)
    figure_blobs = extract_fig_blobs(soup)
    # TODO: not current represented in S2ORC, keep for later
    suppl_blobs = extract_suppl_blobs(soup)
    # TODO: for S2ORC, need to process them into a single ref dict.  need to construct new IDs to match ID conventions.  and update all cite spans.
    #       also, S2ORC table captions are free text without detected reference/citation mentions
    # TODO: may want to keep table representations around
    ref_entries = {}
    for i, (old_table_key, table_blob) in enumerate(sorted(table_blobs.items())):
        # TODO: PMC2557072 table `tbl5` has no label.  skip.
        # TODO: PMC3137981 table `tab1` has no caption text.  skip.
        if not table_blob['label'] or not table_blob['caption']:
            continue
        table_text = table_blob['label'] + ': ' + ' '.join(
            [c['text'] for c in table_blob['caption']]
        ) + '\n' + ' '.join([f['text'] for f in table_blob['footnote']])
        new_table_key = f'TABREF{i}'
        old_key_to_new_key[old_table_key] = new_table_key
        # TODO: skipping over any citations or references in the table for now
        if table_blob['xml']:
            table_content = table_blob['xml'][0]['text']
        ref_entries[new_table_key] = {'text': table_text, 'content': table_content, 'type': 'table'}
    for i, (old_figure_key, figure_blob) in enumerate(sorted(figure_blobs.items())):
        # TODO: double-check, but it seems like figure blobs dont have footnotes parsed out? might be bug
        # TODO: PMC1326260 first figure has no ['label'].  just skip these for now (because no inline references)
        # TODO: PMC2403743 has null-valued caption in `fig1`.  also skip here. fix later.
        if not figure_blob['label'] or not figure_blob['caption']:
            continue
        figure_text = figure_blob['label'] + ': ' + ' '.join([c['text'] for c in figure_blob['caption']])
        new_figure_key = f'FIGREF{i}'
        old_key_to_new_key[old_figure_key] = new_figure_key
        ref_entries[new_figure_key] = {'text': figure_text, 'type': 'figure'}

    # FRONT TAGS
    front_tag = soup.find('front').extract()
    front_dict = process_front_tag(front_tag=front_tag, soup=soup)
    front_dict = postprocess_front_tags_for_s2orc(front_dict)
    front_dict['abstract'] = convert_paragraphs_to_s2orc(front_dict['abstract'], old_key_to_new_key)

    # BACK TAGS
    back_tag = soup.find('back')
    back_dict = {}
    # PMC1139917 doesnt have 'back' tag
    if back_tag is not None:
        back_dict = process_back_tag(back_tag=back_tag)
        # TODO: format bib entries to S2ORC format.  we're already very close, but need a couple changes:
        #       - author blobs include a 'suffix' which defaults to empty string
        #       - issn defaults to empty string
        #       - rename all the bib IDs
        bib_entries = {}
        for i, (old_bib_key, bib_entry) in enumerate(sorted(back_dict['bib_entries'].items())):
            del bib_entry['ref_id']
            new_bib_key = f'BIBREF{i}'
            old_key_to_new_key[old_bib_key] = new_bib_key
            bib_entries[new_bib_key] = bib_entry
    else:
        bib_entries = {}

    if back_dict and back_dict.get('acknowledgements'):
        back_dict['acknowledgements'] = convert_acks_to_s2orc(back_dict['acknowledgements'])

    # BODY TAGS
    body_tag = soup.find('body')
    # PMC1240684 doesnt have 'body' tag
    if body_tag is not None:
        body_dict = process_body_tag(body_tag=body_tag, soup=soup)
        body_text = body_dict['body_text']
    else:
        # Has no body: /disk2/gorpus/20200101/pmc/Br_Foreign_Med_Chir_Rev/PMC5163425.nxml
        body_text = []

    body_text = convert_paragraphs_to_s2orc(body_text, old_key_to_new_key)

    metadata = {
        "title": front_dict['title'],
        "authors": front_dict['authors'],
        "year": front_dict['year'],
        "venue": front_dict['journal_name'],
        "identifiers": {
            "doi": front_dict['doi'],
            "pubmed_id": front_dict['pubmed_id'],
            "pmc_id": front_dict['pmc_id']
        }
    }

    return Paper(
        paper_id=file_id,
        pdf_hash="",
        metadata=metadata,
        abstract=front_dict['abstract'],
        body_text=body_text,
        back_matter=back_dict.get('acknowledgements', []),
        bib_entries=bib_entries,
        ref_entries=ref_entries
    )


if __name__ == '__main__':
    jats_file = 'tests/jats/PMC5828200.nxml'
    paper = convert_jats_xml_to_s2orc_json(jats_file, 'logs')

    jats_file = 'tests/jats/PMC6398430.nxml'
    paper = convert_jats_xml_to_s2orc_json(jats_file, 'logs')

    jats_file = 'tests/jats/PMC7417471.nxml'
    paper = convert_jats_xml_to_s2orc_json(jats_file, 'logs')

    print('done.')