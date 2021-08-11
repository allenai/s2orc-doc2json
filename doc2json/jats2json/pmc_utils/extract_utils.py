
from typing import Dict

import bs4
from bs4 import BeautifulSoup

from doc2json.jats2json.pmc_utils.all_tag_utils import parse_all_paragraphs_in_section


def extract_fig_blobs(body_tag) -> Dict:
    fig_blobs = {}
    for fig_tag in body_tag.find_all('fig'):
        fig = fig_tag.extract()
        label = fig.find('label')
        fig_blobs[fig['id']] = {
            'label': label and label.text,
            'caption': fig.find('caption')
        }
    _update_fig_blobs(fig_blobs)
    return fig_blobs


def _update_fig_blobs(fig_blobs: Dict):
    for fig_blob in fig_blobs.values():
        if fig_blob['caption'] is None:
            continue
        # replace non-p tags w/ p tags in figure caption (mostly dealing with title tags, which weren't being extracted before)
        for tag in fig_blob['caption']:
            if type(tag) == bs4.element.Tag and tag.name != 'p':
                tag.name = 'p'
        par_blobs = parse_all_paragraphs_in_section(sec_tag=fig_blob['caption'], replace_formula=False)
        for par_blob in par_blobs:
            del par_blob['section']
        fig_blob['caption'] = par_blobs


def extract_table_blobs(body_tag) -> Dict:
    # note 1: footnotes dont always exist for each table; hence the if statement
    # note 2: we want to preserve the XML tags for tables, but also need to run it through the regex cleaner for xrefs and other spans
    #         hence, wrapping all of the table XML text into a fake <p> paragraph tag
    table_blobs = {}
    for table_tag in body_tag.find_all('table-wrap'):
        table = table_tag.extract()
        label = table.find('label')
        # TODO: currently restricting to tables with identifiers.  might want to include unreferenced tables once we care more.
        if table.get('id'):
            table_blobs[table['id']] = {
                'label': label and label.text,
                'caption': table.find('caption'),
                'footnote': table.find('table-wrap-foot') if table.find('table-wrap-foot') else BeautifulSoup('<p></p>', 'xml'),
                'xml': BeautifulSoup('<p>' + str(table.find('table')) + '</p>', 'xml')
            }
    _update_table_blobs(table_blobs)
    return table_blobs


def _update_table_blobs(table_blobs: Dict):
    for table_blob in table_blobs.values():
        if table_blob['caption'] is not None:
            # replace non-p tags w/ p tags in table caption (mostly dealing with title tags, which weren't being extracted before)
            for tag in table_blob['caption']:
                if type(tag) == bs4.element.Tag and tag.name != 'p':
                    tag.name = 'p'
            par_blobs = parse_all_paragraphs_in_section(sec_tag=table_blob['caption'], replace_formula=False)
            for par_blob in par_blobs:
                del par_blob['section']
            table_blob['caption'] = par_blobs
        if table_blob['footnote'] is not None:
            par_blobs = parse_all_paragraphs_in_section(sec_tag=table_blob['footnote'], replace_formula=False)
            for par_blob in par_blobs:
                del par_blob['section']
            table_blob['footnote'] = par_blobs
        # note: if we dont include `par_to_text` function, the parser will convert all <p> tags to text via `par_tag.text`
        #       which actually removes all XML tags we wanted to preserve in table.
        #       by passing in str(), we ensure to keep all of those tags
        if table_blob['xml'] is not None:
            par_blobs = parse_all_paragraphs_in_section(sec_tag=table_blob['xml'], par_to_text=str, replace_formula=False)
            for par_blob in par_blobs:
                del par_blob['section']
            table_blob['xml'] = par_blobs


def extract_suppl_blobs(body_tag) -> Dict:
    suppl_blobs = {}
    for suppl_tag in body_tag.find_all('supplementary-material'):
        suppl = suppl_tag.extract()
        # We only care about supplementary material that can be referenced (like figures/tables)
        # for example, we dont care about PMC1139917 which has supplementary material but without an ID
        if 'id' in suppl:
            label = suppl.find('label')
            suppl_blobs[suppl['id']] = {
                'label': label and label.text,
                'caption': suppl.find('caption')
            }
    _update_suppl_blobs(suppl_blobs)
    return suppl_blobs


def _update_suppl_blobs(suppl_blobs: Dict):
    for suppl_blob in suppl_blobs.values():
        if suppl_blob['caption'] is None:
            continue
        par_blobs = parse_all_paragraphs_in_section(sec_tag=suppl_blob['caption'])
        for par_blob in par_blobs:
            del par_blob['section']
        suppl_blob['caption'] = par_blobs
