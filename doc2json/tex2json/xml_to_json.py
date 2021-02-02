import os
import re
import itertools
import bs4
from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict, Tuple
import copy
import latex2mathml.converter

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
        soup = BeautifulSoup(xml_str, 'lxml')
        bib_entry = parse_bib_entry(soup)
        if not bib_entry['raw_text']:
            bib_entry['raw_text'] = bib_string
        return bib_entry
    return None


def replace_ref_tokens(sp: BeautifulSoup, el: bs4.element.Tag, ref_map: Dict):
    """
    Replace all references in element with special tokens
    :param sp:
    :param el:
    :param ref_map:
    :return:
    """
    # replace all citations with cite keyword
    for cite in el.find_all('cit'):
        try:
            target = cite.ref.get('target').replace('bid', 'BIBREF')
            cite.replace_with(sp.new_string(f" {target} "))
        except AttributeError:
            print('Attribute error: ', cite)
            continue

    # replace all non citation references
    for rtag in el.find_all('ref'):
        try:
            if rtag.get('target') and not rtag.get('target').startswith('bid'):
                if rtag.get('target').startswith('cid'):
                    target = rtag.get('target').replace('cid', 'SECREF')
                elif rtag.get('target').startswith('uid'):
                    if rtag.get('target').replace('uid', 'FIGREF') in ref_map:
                        target = rtag.get('target').replace('uid', 'FIGREF')
                    elif rtag.get('target').replace('uid', 'TABREF') in ref_map:
                        target = rtag.get('target').replace('uid', 'TABREF')
                    elif rtag.get('target').replace('uid', 'EQREF') in ref_map:
                        target = rtag.get('target').replace('uid', 'EQREF')
                    elif rtag.get('target').replace('uid', 'FOOTREF') in ref_map:
                        target = rtag.get('target').replace('uid', 'FOOTREF')
                    elif rtag.get('target').replace('uid', 'SECREF') in ref_map:
                        target = rtag.get('target').replace('uid', 'SECREF')
                    else:
                        target = rtag.get('target').upper()
                else:
                    print('Weird ID!')
                    target = rtag.get('target').upper()
                rtag.replace_with(sp.new_string(f" {target} "))
        except AttributeError:
            print('Attribute error: ', rtag)
            continue

    return el


def process_paragraph(sp: BeautifulSoup, para_el: bs4.element.Tag, section_info: List, bib_map: Dict, ref_map: Dict):
    """
    Process one paragraph
    :param sp:
    :param para_el:
    :param section_info:
    :param bib_map:
    :param ref_map:
    :return:
    """
    # replace all ref tokens with special tokens
    para_el = replace_ref_tokens(sp, para_el, ref_map)

    # sub and get corresponding spans of inline formulas
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
            formula_mathml = latex2mathml.converter.convert(ftag.texmath.text)
            formula_dict[formula_key] = (ftag.math.text, ftag.texmath.text, formula_mathml, ref_id)
            ftag.replace_with(sp.new_string(f" {formula_key} "))
        except AttributeError:
            continue

    # remove floats
    for fl in para_el.find_all('float'):
        print('Warning: still has <float/>!')
        fl.decompose()

    # remove notes
    for note in para_el.find_all('note'):
        print('Warning: still has <note/>!')
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
            "ref_id": span.group()
        })

    # get all equation spans
    all_eq_spans = []
    for span in itertools.chain(
            re.finditer(r'(INLINEFORM\d+)', text),
            re.finditer(r'(DISPLAYFORM\d+)', text)
    ):
        try:
            matching_formula = formula_dict[span.group()]
            all_eq_spans.append({
                "start": span.start(),
                "end": span.start() + len(span.group()),
                "text": matching_formula[0],
                "latex": matching_formula[1],
                "mathml": matching_formula[2],
                "ref_id": matching_formula[3]
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
        section=section_info
    )


def process_maketitle(sp: BeautifulSoup, grobid_client: GrobidClient, log_file: str) -> Tuple[str, List]:
    """
    Process maketitle section in soup
    :param sp:
    :param grobid_client:
    :param log_file:
    :return:
    """
    title = ""
    authors = []

    if not sp.maketitle:
        return title, authors
    else:
        # process title
        title = sp.maketitle.title.text
        for formula in sp.author.find_all('formula'):
            formula.decompose()
        # process authors
        author_parts = []
        for tag in sp.author:
            if type(tag) == NavigableString:
                author_parts.append(tag.strip())
            else:
                author_parts.append(tag.text.strip())
        author_parts = [re.sub(r'\s+', ' ', line) for line in author_parts]
        author_parts = [re.sub(r'\s', ' ', line).strip() for line in author_parts]
        author_parts = [part for part in author_parts if part.strip()]
        author_string = ', '.join(author_parts)
        authors = process_author(author_string, grobid_client, log_file)

    sp.maketitle.decompose()
    return title, authors


def process_bibliography_from_tex(sp: BeautifulSoup, client, log_file) -> Dict:
    """
    Parse bibliography from latex
    :return:
    """
    bibkey_map = dict()
    # replace Bibliography with bibliography if needed
    for bibl in sp.find_all("Bibliography"):
        bibl.name = 'bibliography'
    # construct bib map
    if sp.bibliography:
        bib_items = sp.bibliography.find_all('bibitem')
        # map all bib entries
        if bib_items:
            for bi_num, bi in enumerate(bib_items):
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
                        # get URLs from bib entry
                        urls = []
                        for xref in bib_par.find_all('xref'):
                            urls.append(xref.get('url'))
                        bib_entry['urls'] = urls
                        # map to ref id
                        ref_id = normalize_latex_id(bi.get('id'))
                        bib_entry['ref_id'] = ref_id
                        bib_entry['num'] = bi_num
                        bibkey_map[ref_id] = bib_entry
                except AttributeError:
                    print('Attribute error in bib item!', bi)
                    continue
                except TypeError:
                    print('Type error in bib item!', bi)
                    continue
        else:
            for bi_num, p in enumerate(sp.bibliography.find_all('p')):
                try:
                    bib_key, bib_entry = None, None
                    bib_text = p.text
                    bib_name = re.match(r'\[(.*?)\](.*)', bib_text)
                    if bib_name:
                        bib_text = re.sub(r'\s', ' ', bib_text)
                        bib_name = re.match(r'\[(.*?)\](.*)', bib_text)
                        if bib_name:
                            bib_key = bib_name.group(1)
                            bib_entry = process_bibentry(bib_name.group(2), client, log_file)
                    else:
                        bib_lines = bib_text.split('\n')
                        bib_key = re.sub(r'\s', ' ', bib_lines[0])
                        bib_text = re.sub(r'\s', ' ', ' '.join(bib_lines[1:]))
                        bib_entry = process_bibentry(bib_text, client, log_file)
                    if bib_key and bib_entry:
                        # get URLs from bib entry
                        urls = []
                        for xref in p.find_all('xref'):
                            urls.append(xref.get('url'))
                        bib_entry['urls'] = urls
                        bib_entry['num'] = bi_num
                        # map to bib id
                        bibkey_map[bib_key] = bib_entry
                except AttributeError:
                    print('Attribute error in bib item!', p)
                    continue
                except TypeError:
                    print('Type error in bib item!', p)
                    continue
        sp.bibliography.decompose()
    return bibkey_map


def get_section_name(sec):
    """
    Get section name from div tag
    :param sec:
    :return:
    """
    sec_text = ""
    if sec.head:
        sec_text = sec.head.text
    else:
        sec_str = []
        for tag in sec:
            if type(tag) == NavigableString:
                if len(tag.strip()) < 50:
                    sec_str.append(tag.strip())
                else:
                    break
            elif tag.name != 'p':
                if len(tag.text.strip()) < 50:
                    sec_str.append(tag.text.strip())
                else:
                    break
            else:
                break
        sec_text = ' '.join(sec_str).strip()
    return sec_text


def process_sections_from_text(sp: BeautifulSoup) -> Dict:
    """
    Generate section dict and replace with id tokens
    :param sp:
    :return:
    """
    # initialize
    section_map = dict()

    for div0 in sp.find_all('div0'):
        parent = None
        if div0.get('id'):
            sec_num = div0.get('id-text', None)
            ref_id = div0.get('id').replace('cid', 'SECREF')
            div0['s2orc_id'] = ref_id
            section_map[ref_id] = {
                "num": sec_num,
                "text": get_section_name(div0),
                "ref_id": ref_id,
                "parent": None
            }
            parent = ref_id
        if div0.div1:
            for div1 in div0.find_all('div1'):
                if div1.get('id'):
                    sec_num = div1.get('id-text', None)
                    ref_id = div1.get('id').replace('uid', 'SECREF')
                    div1['s2orc_id'] = ref_id
                    section_map[ref_id] = {
                        "num": sec_num,
                        "text": get_section_name(div1),
                        "ref_id": ref_id,
                        "parent": parent
                    }
                for p in itertools.chain(div1.find_all('p'), div1.find_all('proof')):
                    if p.get('id'):
                        sec_num = p.get('id-text', p.hi.get('id-text', None))
                        ref_id = p.get('id').replace('uid', 'SECREF')
                        p['s2orc_id'] = ref_id
                        section_map[ref_id] = {
                            "num": sec_num,
                            "text": p.head.text if p.head else p.hi.text if p.hi else "",
                            "ref_id": ref_id,
                            "parent": parent
                        }
        else:
            for p in itertools.chain(div0.find_all('p'), div0.find_all('proof')):
                if p.get('id'):
                    sec_num = p.get('id-text', p.hi.get('id-text', None))
                    ref_id = p.get('id').replace('uid', 'SECREF')
                    p['s2orc_id'] = ref_id
                    section_map[ref_id] = {
                        "num": sec_num,
                        "text": p.head.text if p.head else p.hi.text if p.hi else "",
                        "ref_id": ref_id,
                        "parent": parent
                    }
    return section_map


def process_equations_from_tex(sp: BeautifulSoup) -> Dict:
    """
    Generate equation dict and replace with id tokens
    :param sp:
    :return:
    """
    equation_map = dict()

    for eq in sp.find_all('formula'):
        try:
            if eq.name and eq.get('type') == 'display':
                if eq.get('id'):
                    ref_id = eq.get('id').replace('uid', 'EQREF')
                    mathml = latex2mathml.converter.convert(eq.texmath.text.strip())
                    equation_map[ref_id] = {
                        "num": eq.get('id-text', None),
                        "text": eq.math.text.strip(),
                        "mathml": mathml,
                        "latex": eq.texmath.text.strip(),
                        "ref_id": ref_id
                    }
                replace_item = sp.new_tag('p')
                equation_copy = copy.copy(eq)
                equation_copy['type'] = 'inline'
                replace_item.insert(0, equation_copy)

                # replace with <p> containing equation as inline
                eq.replace_with(replace_item)

        except AttributeError:
            continue

    return equation_map


def process_footnotes_from_text(sp: BeautifulSoup) -> Dict:
    """
    Process footnote marks
    :param sp:
    :return:
    """
    footnote_map = dict()

    for note in sp.find_all('note'):
        try:
            if note.name and note.get('id'):
                # normalize footnote id
                ref_id = note.get('id').replace('uid', 'FOOTREF')
                # remove equation tex
                for eq in note.find_all('texmath'):
                    eq.decompose()
                # replace all xrefs with link
                for xref in note.find_all('xref'):
                    xref.replace_with(sp.new_string(f" {xref.get('url')} "))
                # clean footnote text
                footnote_text = None
                if note.text:
                    footnote_text = note.text.strip()
                    footnote_text = re.sub(r'\s+', ' ', footnote_text)
                    footnote_text = re.sub(r'\s', ' ', footnote_text)
                # form footnote entry
                footnote_map[ref_id] = {
                    "num": note.get('id-text', None),
                    "text": footnote_text,
                    "ref_id": ref_id
                }
                note.replace_with(sp.new_string(f" {ref_id} "))
        except AttributeError:
            continue

    return footnote_map


def get_figure_map_from_tex(sp: BeautifulSoup) -> Dict:
    """
    Generate figure dict only
    :param sp:
    :return:
    """
    figure_map = dict()

    for fig in sp.find_all('figure'):
        try:
            if fig.name and fig.get('id'):
                # normalize figure id
                ref_id = fig.get('id').replace('uid', 'FIGREF')
                # try to get filenames of figures
                fig_files = []
                if fig.get('file'):
                    fname = fig.get('file') + '.' + fig.get('extension')
                    fig_files.append(os.path.join(fname))
                else:
                    for subfig in fig.find_all('subfigure'):
                        if subfig.get('file'):
                            fig_files.append(subfig.get('file') + '.' + fig.get('extension'))
                # form figmap entry
                figure_map[ref_id] = {
                    "num": fig.get('id-text', None),
                    "text": None, # placeholder
                    "uris": fig_files,
                    "ref_id": ref_id
                }
        except AttributeError:
            continue

    for flt in sp.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'figure':

                # todo: figure where file URIs are with floats
                import pdb
                pdb.set_trace()

                if flt.get('id'):
                    ref_id = flt.get('id').replace('uid', 'FIGREF')
                    # form figmap entry
                    figure_map[ref_id] = {
                        "num": flt.get('id-text', None),
                        "text": None, # placeholder
                        "uris": [],
                        "ref_id": ref_id
                    }
        except AttributeError:
            continue

    return figure_map


def process_figures_from_tex(sp: BeautifulSoup, ref_map: Dict) -> Dict:
    """
    Add figure captions to fig_map and decompose
    :param sp:
    :param ref_map:
    :return:
    """
    for fig in sp.find_all('figure'):
        try:
            if fig.name and fig.get('id'):
                # normalize figure id
                ref_id = fig.get('id').replace('uid', 'FIGREF')
                # remove equation tex
                for eq in fig.find_all('texmath'):
                    eq.decompose()
                # clean caption text
                caption_text = None
                if fig.text:
                    fig = replace_ref_tokens(sp, fig, ref_map)
                    caption_text = fig.text.strip()
                    caption_text = re.sub(r'\s+', ' ', caption_text)
                    caption_text = re.sub(r'\s', ' ', caption_text)
                # add text to figmap entry
                ref_map[ref_id]["text"] = caption_text
        except AttributeError:
            continue
        fig.decompose()

    for flt in sp.find_all('float'):
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
                        flt = replace_ref_tokens(sp, flt, ref_map)
                        caption_text = flt.caption.text.strip()
                        caption_text = re.sub(r'\s+', ' ', caption_text)
                        caption_text = re.sub(r'\s', ' ', caption_text)
                    # form figmap entry
                    ref_map[ref_id]['text'] = caption_text
                flt.decompose()
        except AttributeError:
            continue

    return ref_map


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

            mathml = latex2mathml.converter.convert(latex.strip())
            cells.append({
                "alignment": cell.get('halign'),
                "right-border": cell.get('right-border') == 'true',
                "left-border": cell.get('left-border') == 'true',
                "text": text,
                "mathml": mathml,
                "latex": latex
            })
        table_rep.append({
            "top-border": row.get('top-border') == "true",
            "bottom-border": row.get('bottom-border') == "true",
            "cells": cells
        })
    return table_rep


def get_table_map_from_text(sp: BeautifulSoup, keep_table_contents=True) -> Dict:
    """
    Generate table dict only
    :param sp:
    :param keep_table_contents:
    :return:
    """
    table_map = dict()

    for tab in sp.find_all('table'):
        try:
            # skip inline tables
            if tab.get('rend') == 'inline':
                continue
            # process them
            if tab.name and tab.get('id'):
                # normalize table id
                ref_id = tab.get('id').replace('uid', 'TABREF')
                # form tabmap entry
                table_map[ref_id] = {
                    "num": tab.get('id-text', None),
                    "text": None,   # placeholder
                    "latex": extract_table(tab) if keep_table_contents else None,
                    "ref_id": ref_id
                }
                for row in tab.find_all('row'):
                    row.decompose()
        except AttributeError:
            continue

    for flt in sp.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'table':
                if flt.get('id'):
                    # normalize table id
                    ref_id = flt.get('id').replace('uid', 'TABREF')
                    # form tabmap entry
                    table_map[ref_id] = {
                        "num": flt.get('id-text', None),
                        "text": None,   # placeholder
                        "latex": extract_table(flt) if keep_table_contents else None,
                        "ref_id": ref_id
                    }
                    for row in flt.find_all('row'):
                        row.decompose()
        except AttributeError:
            continue

    return table_map


def process_tables_from_tex(sp: BeautifulSoup, ref_map: Dict) -> Dict:
    """
    Generate table dict and replace with id tokens
    :param sp:
    :param ref_map:
    :return:
    """
    for tab in sp.find_all('table'):
        try:
            # skip inline tables
            if tab.get('rend') == 'inline':
                continue
            # process them
            if tab.name and tab.get('id'):
                # normalize table id
                ref_id = tab.get('id').replace('uid', 'TABREF')
                # remove equation tex from caption and clean and resolve refs
                if tab.caption:
                    caption_el = replace_ref_tokens(sp, tab.caption, ref_map)
                    for eq in caption_el.find_all('texmath'):
                        eq.decompose()
                    caption_text = caption_el.text.strip()
                elif tab.head:
                    head_el = replace_ref_tokens(sp, tab.head, ref_map)
                    for eq in head_el.find_all('texmath'):
                        eq.decompose()
                    caption_text = head_el.text.strip()
                elif tab.p:
                    caption_parts = []
                    for tab_p in tab.find_all('p'):
                        p_el = replace_ref_tokens(sp, tab_p, ref_map)
                        for eq in p_el.find_all('texmath'):
                            eq.decompose()
                        caption_parts.append(p_el.text.strip())
                    caption_text = ' '.join(caption_parts)
                else:
                    tab_el = replace_ref_tokens(sp, tab, ref_map)
                    caption_text = tab_el.text.strip()
                if caption_text:
                    caption_text = re.sub(r'\s+', ' ', caption_text)
                    caption_text = re.sub(r'\s', ' ', caption_text)
                # form tabmap entry
                ref_map[ref_id]['text'] = caption_text
        except AttributeError:
            continue
        tab.decompose()

    for flt in sp.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'table':
                if flt.get('id'):
                    # normalize table id
                    ref_id = flt.get('id').replace('uid', 'TABREF')
                    # remove equation tex
                    if flt.caption:
                        caption_el = replace_ref_tokens(sp, flt.caption, ref_map)
                        for eq in caption_el.find_all('texmath'):
                            eq.decompose()
                        caption_text = caption_el.text.strip()
                    elif flt.head:
                        head_el = replace_ref_tokens(sp, flt.head, ref_map)
                        for eq in head_el.find_all('texmath'):
                            eq.decompose()
                        caption_text = head_el.text.strip()
                    elif flt.p:
                        caption_parts = []
                        for tab_p in flt.find_all('p'):
                            p_el = replace_ref_tokens(sp, tab_p, ref_map)
                            for eq in p_el.find_all('texmath'):
                                eq.decompose()
                            caption_parts.append(p_el.text.strip())
                        caption_text = ' '.join(caption_parts)
                    else:
                        tab_el = replace_ref_tokens(sp, flt, ref_map)
                        caption_text = tab_el.text.strip()
                    if caption_text:
                        caption_text = re.sub(r'\s+', ' ', caption_text)
                        caption_text = re.sub(r'\s', ' ', caption_text)
                    # form tabmap entry
                    ref_map[ref_id]['text'] = caption_text
                flt.decompose()
        except AttributeError:
            continue

    return ref_map


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


def process_abstract_from_tex(sp: BeautifulSoup, bib_map: Dict, ref_map: Dict) -> List[Dict]:
    """
    Parse abstract from soup
    :param sp:
    :param bib_map:
    :param ref_map:
    :return:
    """
    abstract_text = []
    if sp.abstract:
        for p in sp.abstract.find_all('p'):
            abstract_text.append(
                process_paragraph(sp, p, [(None, "Abstract")], bib_map, ref_map)
            )
        sp.abstract.decompose()
    else:
        p_tags = [tag for tag in sp.std if tag.name == 'p' and not tag.get('s2orc_id', None)]
        if p_tags:
            for p in p_tags:
                abstract_text.append(
                    process_paragraph(sp, p, [(None, "Abstract")], bib_map, ref_map)
                )
                p.decompose()
    return [para.as_json() for para in abstract_text]


def process_body_text_from_tex(soup: BeautifulSoup, bib_map: Dict, ref_map: Dict) -> List[Dict]:
    """
    Parse body text from soup
    :param soup:
    :param bib_map:
    :param ref_map:
    :return:
    """
    # TODO FIX BODY TEXT PARAGRAPH PROCESSING
    raise NotImplementedError
    # section_title = ''
    # body_text = []
    #
    # # check if any body divs
    # div0s = soup.find_all('div0')
    #
    # if div0s:
    #     # process all divs
    #     for div in div0s:
    #         for el in div:
    #             try:
    #                 if el.name == 'head':
    #                     section_title = el.text
    #                 # if paragraph treat as paragraph if any text
    #                 elif el.name == 'p' or el.name == 'proof':
    #                     if el.text:
    #                         body_text.append(
    #                             process_paragraph(soup, el, section_title, bib_map, ref_map)
    #                         )
    #                 # if subdivision, treat each paragraph unit separately
    #                 elif el.name == 'div1':
    #                     if el.head and el.head.text:
    #                         section_title = el.head.text
    #                     for p in itertools.chain(el.find_all('p'), el.find_all('proof')):
    #                         body_text.append(
    #                             process_paragraph(soup, p, section_title, bib_map, ref_map)
    #                         )
    #                         p.decompose()
    #                 if el.name:
    #                     el.decompose()
    #             except AttributeError:
    #                 continue
    # else:
    #     # get all paragraphs
    #     paras = soup.find_all('p')
    #
    #     # figure out where to start processing
    #     start_ind = 0
    #     for p_ind, p in enumerate(paras):
    #         start_ind = p_ind
    #         break
    #
    #     # process all paragraphs
    #     for p in paras[start_ind:]:
    #         body_text.append(
    #             process_paragraph(soup, p, "", bib_map, ref_map)
    #         )
    #         p.decompose()
    #
    # return [para.as_json() for para in body_text]


def convert_xml_to_s2orc(sp: BeautifulSoup, file_id: str, year_str: str, log_file: str) -> Paper:
    """
    Convert a bunch of xml to gorc format
    :param sp:
    :param file_id:
    :param year_str:
    :param log_file:
    :return:
    """
    def decompose_tags_before_title(some_soup):
        # decompose all tags before title
        for tag in some_soup.std:
            if type(tag) == bs4.element.Tag:
                if tag.name != 'maketitle' and tag.name != 'title':
                    tag.decompose()
                else:
                    break
        return some_soup

    # create grobid client
    client = GrobidClient()

    print('parsing xml to s2orc format...')

    # replace unexpected tags with floats
    for mn in sp.find_all("unexpected"):
        mn.name = 'float'

    # decompose tags before title (TODO: not sure why but have to run twice)
    sp = decompose_tags_before_title(sp)
    sp = decompose_tags_before_title(sp)

    # process maketitle info
    title, authors = process_maketitle(sp, client, log_file)

    # processing of bibliography entries
    # TODO: look into why authors aren't processing
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

    # get figure map
    figure_map = get_figure_map_from_tex(sp)

    # get table_map
    table_map = get_table_map_from_text(sp)

    # combine references in one dict
    refkey_map = combine_ref_maps(equation_map, figure_map, table_map, footnote_map, section_map)

    # process and replace figures
    refkey_map = process_figures_from_tex(sp, refkey_map)

    # process and replace tables
    refkey_map = process_tables_from_tex(sp, refkey_map)

    # decompose all remaining floats
    for flt in sp.find_all('float'):
        flt.decompose()

    # process abstract if possible
    abstract = process_abstract_from_tex(sp, bibkey_map, refkey_map)

    # process body text
    body_text = process_body_text_from_tex(sp, bibkey_map, refkey_map)

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
            soup = BeautifulSoup(xml, "lxml")
            paper = convert_xml_to_s2orc(soup, file_id, year, log_file)
            return paper
        except UnicodeDecodeError:
            with open(log_file, 'a+') as log_f:
                log_f.write(f'{file_id},err_unicode_decode\n')
            raise UnicodeDecodeError
