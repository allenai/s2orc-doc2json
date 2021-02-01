import os
import shutil
import re
import itertools
import bs4
from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict
import copy

from doc2json.pdf2json.grobid.grobid_client import GrobidClient
from doc2json.utils.grobid_util import parse_bib_entry, get_author_data_from_grobid_xml
from doc2json.s2orc import Paper, Paragraph


def normalize_latex_id(latex_id: str):
    str_norm = latex_id.upper().replace('_', '')
    if str_norm.startswith('BID'):
        return str_norm.replace('BID', 'BIBREF')
    if str_norm.startswith('CID'):
        return str_norm.replace('CID', 'SECREF')
    if str_norm.startswith('FORMULA'):
        return str_norm.replace('FORMULA', 'EQREF')
    return str_norm


def process_author(
        author_text: str,
        grobid_client: GrobidClient,
        logfile: str
) -> List[Dict]:
    """
    Process authors
    :param author_text:
    :param grobid_client:
    :param logfile:
    :return:
    """
    if author_text:
        author_xml_str = grobid_client.process_header_names(author_text, logfile)
        if author_xml_str:
            author_soup = BeautifulSoup(author_xml_str, 'xml')
            author_entry = get_author_data_from_grobid_xml(author_soup)
            return author_entry

    return [{
        "first": "",
        "middle": [],
        "last": author_text,
        "suffix": "",
        "affiliation": {},
        "email": ""
    }]


def process_bibentry(bib_text: str, grobid_client: GrobidClient, logfile: str):
    """
    Process one bib entry text into title, authors, etc
    :param bib_text:
    :param grobid_client:
    :param logfile:
    :return:
    """
    if not bib_text:
        return None
    bib_lines = bib_text.split('\n')
    bib_lines = [re.sub(r'\s+', ' ', line) for line in bib_lines]
    bib_lines = [re.sub(r'\s', ' ', line).strip() for line in bib_lines]
    bib_string = ' '.join(bib_lines)
    xml_str = grobid_client.process_citation(bib_string, logfile)
    if xml_str:
        soup = BeautifulSoup(xml_str, 'xml')
        return parse_bib_entry(soup)
    return None


def process_paragraph(sp: BeautifulSoup, para_el: bs4.element.Tag, section_name: str, ref_map: Dict):
    """
    Process one paragraph
    :param sp:
    :param para_el:
    :param section_name:
    :param ref_map:
    :return:
    """
    # replace all citations with cite keyword
    for cite in para_el.find_all('cit'):
        try:
            target = cite.ref.get('target').replace('bid', 'BIBREF')
            cite.replace_with(sp.new_string(f" {target} "))
        except AttributeError:
            continue

    # replace formulas with formula text and get corresponding spans
    formula_dict = dict()
    inline_key_ind = 0
    display_key_ind = 0
    for ftag in para_el.find_all('formula'):
        try:
            # if formula has ref id, treat as display formula
            if ftag.get('id'):
                formula_key = f'DISPLAYFORM{display_key_ind}'
                ref_id = ftag.get('id').replace('uid', 'EQREF')
                display_key_ind += 1
            # else, treat as inline
            else:
                formula_key = f'INLINEFORM{inline_key_ind}'
                ref_id = None
                inline_key_ind += 1
            formula_dict[formula_key] = (ftag.math.text, ftag.texmath.text, ref_id)
            ftag.replace_with(sp.new_string(f" {formula_key} "))
        except AttributeError:
            continue

    # replace all non citation references
    ref_set = set([])
    for rtag in para_el.find_all('ref'):
        try:
            if rtag.get('target') and not rtag.get('target').startswith('bid'):
                if rtag.get('target').startswith('cid'):
                    rtag_string = rtag.get('target').replace('cid', 'SECREF')
                elif rtag.get('target').startswith('uid'):
                    if rtag.get('target').replace('uid', 'FIGREF') in ref_map:
                        rtag_string = rtag.get('target').replace('uid', 'FIGREF')
                    elif rtag.get('target').replace('uid', 'TABREF') in ref_map:
                        rtag_string = rtag.get('target').replace('uid', 'TABREF')
                    elif rtag.get('target').replace('uid', 'EQREF') in ref_map:
                        rtag_string = rtag.get('target').replace('uid', 'EQREF')
                    elif rtag.get('target').replace('uid', 'FOOTREF') in ref_map:
                        rtag_string = rtag.get('target').replace('uid', 'FOOTREF')
                    elif rtag.get('target').replace('uid', 'SECREF') in ref_map:
                        rtag_string = rtag.get('target').replace('uid', 'SECREF')
                    else:
                        rtag_string = rtag.get('target').upper()
                else:
                    print('Weird ID!')
                    rtag_string = rtag.get('target').upper()
                ref_set.add(rtag_string)
                rtag.replace_with(sp.new_string(f" {rtag_string} "))
        except AttributeError:
            continue

    # remove floats
    for fl in para_el.find_all('float'):
        fl.decompose()

    # remove notes
    for note in para_el.find_all('note'):
        note.decompose()

    # substitute space characters
    text = re.sub(r'\s+', ' ', para_el.text)
    text = re.sub(r'\s', ' ', text)

    # get all cite spans
    all_cite_spans = []
    for span in re.finditer(r'(BIBREF\d+)', text):
        all_cite_spans.append({
            "start": span.start(),
            "end": span.start() + len(span.group()),
            "text": None,
            "latex": None,
            "ref_id": span.group()
        })

    # get all ref spans
    all_ref_spans = []
    for span in itertools.chain(
        re.finditer(r'(FIGREF\d+)', text),
        re.finditer(r'(TABREF\d+)', text),
        re.finditer(r'(EQREF\d+)', text),
        re.finditer(r'(FOOTREF\d+)', text),
        re.finditer(r'(SECREF\d+)', text),
    ):
        all_ref_spans.append({
            "start": span.start(),
            "end": span.start() + len(span.group()),
            "text": None,
            "latex": None,
            "ref_id": span.group()
        })

    # get all equation spans
    all_eq_spans = []
    for span in itertools.chain(
            re.finditer(r'(INLINEFORM\d+)', text),
            re.finditer(r'(DISPLAYFORM\d+)', text)
    ):
        try:
            all_eq_spans.append({
                "start": span.start(),
                "end": span.start() + len(span.group()),
                "text": formula_dict[span.group()][0],
                "latex": formula_dict[span.group()][1],
                "ref_id": formula_dict[span.group()][2]
            })
        except KeyError:
            continue

    # assert all align
    for cite_span in all_cite_spans:
        assert text[cite_span['start']:cite_span['end']] == cite_span['ref_id']
    for ref_span in all_ref_spans:
        assert text[ref_span['start']:ref_span['end']] == ref_span['ref_id']

    return Paragraph(
        text=text,
        cite_spans=all_cite_spans,
        ref_spans=all_ref_spans,
        eq_spans=all_eq_spans,
        # TODO: get section number and section hierarchy
        section=[(None, section_name)]
    )


def process_bibliography_from_tex(soup, client, log_file) -> Dict:
    """
    Parse bibliography from latex
    :return:
    """
    bibkey_map = dict()
    # construct bib map
    if soup.Bibliography:
        bib_items = soup.Bibliography.find_all('bibitem')
        # map all bib entries
        if bib_items:
            for bi in bib_items:
                try:
                    if not bi.get('id'):
                        continue
                    # get bib entry text and process it
                    bib_par = bi.find_parent('p')
                    if bib_par.text:
                        bib_entry = process_bibentry(bib_par.text, client, log_file)
                    else:
                        next_tag = bib_par.findNext('p')
                        if not next_tag.find('bibitem') and next_tag.text:
                            bib_entry = process_bibentry(next_tag.text, client, log_file)
                        else:
                            bib_entry = None
                    # if processed successfully, add to map
                    if bib_entry:
                        ref_id = normalize_latex_id(bi.get('id'))
                        bib_entry.ref_id = ref_id
                        bibkey_map[ref_id] = bib_entry.as_json()
                except AttributeError:
                    continue
                except TypeError:
                    continue
        else:
            for p in soup.Bibliography.find_all('p'):
                try:
                    bib_text = p.text
                    bib_name = re.match(r'\[(.*?)\](.*)', bib_text)
                    if bib_name:
                        bib_text = re.sub(r'\s', ' ', bib_text)
                        bib_name = re.match(r'\[(.*?)\](.*)', bib_text)
                        if bib_name:
                            bib_key = bib_name.group(1)
                            bib_entry = process_bibentry(bib_name.group(2), client, log_file)
                            if bib_entry:
                                bib_entry.ref_id = bib_key
                                bibkey_map[bib_key] = bib_entry.as_json()
                    else:
                        bib_lines = bib_text.split('\n')
                        bib_key = re.sub(r'\s', ' ', bib_lines[0])
                        bib_text = re.sub(r'\s', ' ', ' '.join(bib_lines[1:]))
                        bib_entry = process_bibentry(bib_text, client, log_file)
                        if bib_entry:
                            bibkey_map[bib_key] = bib_entry.as_json()
                except AttributeError:
                    continue
                except TypeError:
                    continue
        soup.Bibliography.decompose()
    return bibkey_map


def process_sections_from_text(soup: BeautifulSoup) -> Dict:
    """
    Generate section dict and replace with id tokens
    :param soup:
    :return:
    """
    # TODO: get section hierarchy
    section_map = dict()

    for div0 in soup.find_all('div0'):
        if div0.get('id'):
            ref_id = div0.get('id').replace('cid', 'SECREF')
            section_map[ref_id] = {
                "text": div0.head.text if div0.head else "",
                "latex": None,
                "ref_id": ref_id
            }
        if div0.div1:
            for div1 in div0.find_all('div1'):
                if div1.get('id'):
                    ref_id = div1.get('id').replace('uid', 'SECREF')
                    section_map[ref_id] = {
                        "text": div1.head.text if div1.head else "",
                        "latex": None,
                        "ref_id": ref_id
                    }
                for p in itertools.chain(div1.find_all('p'), div1.find_all('proof')):
                    if p.get('id'):
                        ref_id = p.get('id').replace('uid', 'SECREF')
                        section_map[ref_id] = {
                            "text": p.head.text if p.head else p.hi.text if p.hi else "",
                            "latex": p.get('id-text') if p.get('id-text') else None,
                            "ref_id": ref_id
                        }
        else:
            for p in itertools.chain(div0.find_all('p'), div0.find_all('proof')):
                if p.get('id'):
                    ref_id = p.get('id').replace('uid', 'SECREF')
                    section_map[ref_id] = {
                        "text": p.head.text if p.head else p.hi.text if p.hi else "",
                        "latex": p.get('id-text') if p.get('id-text') else None,
                        "ref_id": ref_id
                    }
    return section_map


def process_equations_from_tex(soup: BeautifulSoup) -> Dict:
    """
    Generate equation dict and replace with id tokens
    :param soup:
    :return:
    """
    equation_map = dict()

    for eq in soup.find_all('formula'):
        try:
            if eq.name and eq.get('type') == 'display':

                if eq.get('id'):
                    ref_id = eq.get('id').replace('uid', 'EQREF')
                    equation_map[ref_id] = {
                        "text": eq.math.text.strip(),
                        "latex": eq.texmath.text.strip(),
                        "ref_id": ref_id
                    }
                replace_item = copy.copy(eq)
                replace_item['type'] = 'inline'

                # append formula keyword to previous <p>
                cur_tag = eq
                for _ in range(3):
                    prev_tag = cur_tag.previous_sibling
                    if not prev_tag:
                        break
                    if prev_tag.name == 'p':
                        prev_tag.insert(len(prev_tag.contents), NavigableString(' '))
                        prev_tag.insert(len(prev_tag.contents), replace_item)
                        break
                    else:
                        cur_tag = prev_tag

                # decompose quoted equations
                eq.decompose()

        except AttributeError:
            continue

    return equation_map


def process_footnotes_from_text(soup: BeautifulSoup) -> Dict:
    """
    Process footnote marks
    :param soup:
    :return:
    """
    footnote_map = dict()

    for note in soup.find_all('note'):
        try:
            if note.name and note.get('id'):
                # normalize footnote id
                ref_id = note.get('id').replace('uid', 'FOOTREF')
                # remove equation tex
                for eq in note.find_all('texmath'):
                    eq.decompose()
                # clean footnote text
                footnote_text = None
                if note.text:
                    footnote_text = note.text.strip()
                    footnote_text = re.sub(r'\s+', ' ', footnote_text)
                    footnote_text = re.sub(r'\s', ' ', footnote_text)
                # form footnote entry
                footnote_map[ref_id] = {
                    "text": note.get('id-text') if note.get('id-text') else None,
                    "caption": footnote_text,
                    "latex": None,
                    "ref_id": ref_id
                }
                note.replace_with(soup.new_string(f" {ref_id} "))
        except AttributeError:
            continue

    return footnote_map


def process_figures_from_tex(soup: BeautifulSoup) -> Dict:
    """
    Generate figure dict and replace with id tokens
    :param soup:
    :return:
    """
    figure_map = dict()

    for fig in soup.find_all('figure'):
        try:
            if fig.name and fig.get('id'):
                # normalize figure id
                ref_id = fig.get('id').replace('uid', 'FIGREF')
                # try to get filenames of figures
                if fig.get('file'):
                    filename = fig.get('file')
                else:
                    subfiles = []
                    for subfig in fig.find_all('subfigure'):
                        if subfig.get('file'):
                            subfiles.append(subfig.get('file'))
                    filename = '|'.join(subfiles)
                # remove equation tex
                for eq in fig.find_all('texmath'):
                    eq.decompose()
                # clean caption text
                caption_text = None
                if fig.text:
                    caption_text = fig.text.strip()
                    caption_text = re.sub(r'\s+', ' ', caption_text)
                    caption_text = re.sub(r'\s', ' ', caption_text)
                # form figmap entry
                figure_map[ref_id] = {
                    "text": fig.get('id-text') if fig.get('id-text') else None,
                    "caption": caption_text,
                    "latex": filename,
                    "ref_id": ref_id
                }
        except AttributeError:
            continue
        fig.decompose()

    for flt in soup.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'figure':
                if flt.get('id'):
                    ref_id = flt.get('id').replace('uid', 'FIGREF')
                    # remove equation tex
                    for eq in flt.find_all('texmath'):
                        eq.decompose()
                    # clean caption text
                    caption_text = None
                    if flt.caption:
                        caption_text = flt.caption.text.strip()
                        caption_text = re.sub(r'\s+', ' ', caption_text)
                        caption_text = re.sub(r'\s', ' ', caption_text)
                    # form figmap entry
                    figure_map[ref_id] = {
                        "text": flt.get('id-text') if flt.get('id-text') else None,
                        "caption": caption_text,
                        "latex": None,
                        "ref_id": ref_id
                    }
                flt.decompose()
        except AttributeError:
            continue

    return figure_map


def extract_table(table: BeautifulSoup) -> List:
    """
    Extract table values from table entry
    :param table:
    :return:
    """
    table_rep = []
    for row in table.find_all('row'):
        cells = []
        for cell in row.find_all('cell'):

            text_items = []
            latex_items = []

            for child in cell:

                if type(child) == NavigableString:
                    text_items.append(str(child))
                    latex_items.append(str(child))
                elif child.name == 'formula':
                    text_items.append(child.math.text)
                    latex_items.append(child.texmath.text)
                else:
                    text_items.append(child.text)
                    latex_items.append(child.text)

            text = ' '.join(text_items)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\s', ' ', text)

            latex = ' '.join(latex_items)
            latex = re.sub(r'\s+', ' ', latex)

            cells.append({
                "alignment": cell.get('halign'),
                "right-border": cell.get('right-border') == 'true',
                "left-border": cell.get('left-border') == 'true',
                "text": text,
                "latex": latex
            })
        table_rep.append({
            "top-border": row.get('top-border') == "true",
            "bottom-border": row.get('bottom-border') == "true",
            "cells": cells
        })
    return table_rep


def process_tables_from_tex(soup: BeautifulSoup, keep_table_contents=True) -> Dict:
    """
    Generate table dict and replace with id tokens
    :param soup:
    :param keep_table_contents:
    :return:
    """
    table_map = dict()

    for tab in soup.find_all('table'):
        try:
            if tab.name and tab.get('id'):
                # normalize table id
                ref_id = tab.get('id').replace('uid', 'TABREF')
                # remove equation tex from caption and clean
                caption_text = None
                if tab.caption:
                    for eq in tab.caption.find_all('texmath'):
                        eq.decompose()
                    caption_text = tab.caption.text.strip()
                elif tab.head:
                    for eq in tab.head.find_all('texmath'):
                        eq.decompose()
                    caption_text = tab.head.text.strip()
                if caption_text:
                    caption_text = re.sub(r'\s+', ' ', caption_text)
                    caption_text = re.sub(r'\s', ' ', caption_text)
                # form tabmap entry
                table_map[ref_id] = {
                    "text": tab.get('id-text') if tab.get('id-text') else None,
                    "caption": caption_text,
                    "latex": extract_table(tab) if keep_table_contents else None,
                    "ref_id": ref_id
                }
        except AttributeError:
            continue
        tab.decompose()

    for flt in soup.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'table':
                if flt.get('id'):
                    # normalize table id
                    ref_id = flt.get('id').replace('uid', 'TABREF')
                    # remove equation tex
                    caption_text = None
                    if flt.caption:
                        for eq in flt.caption.find_all('texmath'):
                            eq.decompose()
                        caption_text = flt.caption.text.strip()
                    elif flt.head:
                        for eq in flt.head.find_all('texmath'):
                            eq.decompose()
                        caption_text = flt.head.text.strip()
                    if caption_text:
                        caption_text = re.sub(r'\s+', ' ', caption_text)
                        caption_text = re.sub(r'\s', ' ', caption_text)
                    # form tabmap entry
                    table_map[ref_id] = {
                        "text": flt.get('id-text') if flt.get('id-text') else None,
                        "caption": caption_text,
                        "latex": extract_table(flt) if keep_table_contents else None,
                        "ref_id": ref_id
                    }
                flt.decompose()
        except AttributeError:
            continue

    return table_map


def combine_ref_maps(eq_map: Dict, fig_map: Dict, tab_map: Dict, foot_map: Dict, sec_map: Dict):
    """
    Combine all items with ref ids into one map
    :param eq_map:
    :param fig_map:
    :param tab_map:
    :param sec_map:
    :return:
    """
    ref_map = dict()
    for k, v in eq_map.items():
        v['type'] = 'equation'
        ref_map[k] = v
    for k, v in fig_map.items():
        v['type'] = 'figure'
        ref_map[k] = v
    for k, v in tab_map.items():
        v['type'] = 'table'
        ref_map[k] = v
    for k, v in foot_map.items():
        v['type'] = 'footnote'
        ref_map[k] = v
    for k, v in sec_map.items():
        v['type'] = 'section'
        ref_map[k] = v
    return ref_map


def process_abstract_from_tex(soup: BeautifulSoup, ref_map: Dict) -> List[Dict]:
    """
    Parse abstract from soup
    :param soup:
    :param ref_map:
    :return:
    """
    abstract_text = []
    if soup.abstract:
        for p in soup.abstract.find_all('p'):
            abstract_text.append(
                process_paragraph(soup, p, "Abstract", ref_map)
            )
        soup.abstract.decompose()
    return [para.as_json() for para in abstract_text]


def process_body_text_from_tex(soup: BeautifulSoup, ref_map: Dict) -> List[Dict]:
    """
    Parse body text from soup
    :param soup:
    :param ref_map:
    :return:
    """
    section_title = ''
    body_text = []

    # check if any body divs
    div0s = soup.find_all('div0')

    if div0s:
        # process all divs
        for div in div0s:
            for el in div:
                try:
                    if el.name == 'head':
                        section_title = el.text
                    # if paragraph treat as paragraph if any text
                    elif el.name == 'p' or el.name == 'proof':
                        if el.text:
                            body_text.append(
                                process_paragraph(soup, el, section_title, ref_map)
                            )
                    # if subdivision, treat each paragraph unit separately
                    elif el.name == 'div1':
                        if el.head and el.head.text:
                            section_title = el.head.text
                        for p in itertools.chain(el.find_all('p'), el.find_all('proof')):
                            body_text.append(
                                process_paragraph(soup, p, section_title, ref_map)
                            )
                            p.decompose()
                    if el.name:
                        el.decompose()
                except AttributeError:
                    continue
    else:
        # get all paragraphs
        paras = soup.find_all('p')

        # figure out where to start processing
        start_ind = 0
        for p_ind, p in enumerate(paras):
            start_ind = p_ind
            break

        # process all paragraphs
        for p in paras[start_ind:]:
            body_text.append(
                process_paragraph(soup, p, "", ref_map)
            )
            p.decompose()

    return [para.as_json() for para in body_text]


def convert_xml_to_s2orc(sp: BeautifulSoup, file_id: str, year_str: str, log_file: str) -> Paper:
    """
    Convert a bunch of xml to gorc format
    :param sp:
    :param file_id:
    :param year_str:
    :param log_file:
    :return:
    """
    # create grobid client
    client = GrobidClient()

    print('parsing xml to s2orc format...')

    import ipdb
    ipdb.set_trace()

    # remove what is most likely noise
    for mn in sp.find_all("unexpected"):
        mn.decompose()

    # processing of bibliography entries
    bibkey_map = process_bibliography_from_tex(sp, client, log_file)

    # no bibliography entries
    if not bibkey_map:
        with open(log_file, 'a+') as bib_f:
            bib_f.write(f'{file_id},warn_no_bibs\n')

    # process section headers
    section_map = process_sections_from_text(sp)

    # process and replace non-inline equations
    equation_map = process_equations_from_tex(sp)

    # process footnote markers
    footnote_map = process_footnotes_from_text(sp)

    # process and replace figures
    figure_map = process_figures_from_tex(sp)

    # process and replace tables
    table_map = process_tables_from_tex(sp)

    # combine references in one dict
    refkey_map = combine_ref_maps(equation_map, figure_map, table_map, footnote_map, section_map)

    # decompose all remaining floats
    for flt in sp.find_all('float'):
        flt.decompose()

    # try to get title/author if not exist
    if sp.title:
        title = sp.title.text.strip()
    else:
        title = ""

    # try to get authors
    authors = []
    for author in sp.find_all('author'):
        authors.append({
            "first": "",
            "middle": [],
            "last": author.text.strip(),
            "suffix": "",
            "affiliation": {},
            "email": ""
        })

    # process abstract if possible
    abstract = process_abstract_from_tex(sp, refkey_map)

    # process body text
    body_text = process_body_text_from_tex(sp, refkey_map)

    # skip if no body text parsed
    if not body_text:
        with open(log_file, 'a+') as body_f:
            body_f.write(f'{file_id},warn_no_body\n')

    # abstract = [para.as_json() for para in abstract]

    metadata = {
        "title": title,
        "authors": authors,
        "year": year_str
    }

    return Paper(
        paper_id=file_id,
        pdf_hash="",
        metadata=metadata,
        abstract=abstract,
        body_text=body_text,
        back_matter=[],
        bib_entries=bibkey_map,
        ref_entries=refkey_map
    )


def convert_latex_xml_to_s2orc_json(xml_fpath: str, log_dir: str) -> Paper:
    """
    :param xml_fpath:
    :param log_dir:
    :return:
    """
    assert os.path.exists(xml_fpath)

    # get file id
    file_id = str(os.path.splitext(xml_fpath)[0]).split('/')[-1]

    # try to get year from file name
    year = file_id.split('.')[0][:2]
    if year.isdigit():
        year = int(year)
        if year < 20:
            year += 2000
        else:
            year += 1900
        year = str(year)
    else:
        year = ""

    # log file
    log_file = os.path.join(log_dir, 'failed.log')

    with open(xml_fpath, 'r') as f:
        try:
            xml = f.read()
            soup = BeautifulSoup(xml, "xml")
            paper = convert_xml_to_s2orc(soup, file_id, year, log_file)
            return paper
        except UnicodeDecodeError:
            with open(log_file, 'a+') as log_f:
                log_f.write(f'{file_id},err_unicode_decode\n')
            raise UnicodeDecodeError
