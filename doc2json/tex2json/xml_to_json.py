import os
import re
import itertools
import bs4
from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict, Tuple, Optional
import copy
import latex2mathml.converter

from doc2json.grobid2json.grobid.grobid_client import GrobidClient
from doc2json.utils.grobid_util import parse_bib_entry, get_author_data_from_grobid_xml
from doc2json.s2orc import Paper, Paragraph


SKIP_TAGS = {
    'clearpage',
    'colorpool',
    'newpage',
    'tableofcontents'
}

TEXT_TAGS = {
    'p',
    'proof',
    'caption'
}


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
                    elif rtag.get('target').replace('uid', 'SECREFU') in ref_map:
                        target = rtag.get('target').replace('uid', 'SECREFU')
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


def process_list_el(sp: BeautifulSoup, list_el: bs4.element.Tag, section_info: List, bib_map: Dict, ref_map: Dict):
    """
    Process list element
    :param sp:
    :param list_el:
    :param section_info:
    :param bib_map:
    :param ref_map:
    :return:
    """
    # TODO: currently parsing list as a list of paragraphs (append numbers to start of each entry in ordered lists)
    list_items = []
    for item in list_el.find_all('item'):
        # skip itemize settings
        if item.text.strip().startswith('[') and item.text.strip().endswith(']'):
            continue
        # try processing as paragraph
        list_num = item.get('id-text', None)
        item_as_para = process_paragraph(sp, item, section_info, bib_map, ref_map)
        # append list number if ordered
        if list_num:
            list_num_str = f'{list_num}. '
            # iterate cite spans
            new_cite_spans = []
            for span in item_as_para.cite_spans:
                new_cite_spans.append({
                    "start": span['start'] + len(list_num_str),
                    "end": span['end'] + len(list_num_str),
                    "text": span['text']
                })
            # iterate ref spans
            new_ref_spans = []
            for span in item_as_para.ref_spans:
                new_ref_spans.append({
                    "start": span['start'] + len(list_num_str),
                    "end": span['end'] + len(list_num_str),
                    "text": span['text']
                })
            # iterate equation spans
            new_eq_spans = []
            for span in item_as_para.eq_spans:
                new_eq_spans.append({
                    "start": span['start'] + len(list_num_str),
                    "end": span['end'] + len(list_num_str),
                    "text": span['text'],
                    "latex": span['latex'],
                    "ref_id": span['ref_id']
                })
            new_para = Paragraph(
                text=list_num_str + item_as_para.text,
                cite_spans=new_cite_spans,
                ref_spans=new_ref_spans,
                eq_spans=new_eq_spans,
                section=item_as_para.section
            )
        else:
            new_para = item_as_para
        list_items.append(new_para)
    return list_items


def process_navstring(str_el: NavigableString, section_info: List):
    """
    Process one NavigableString
    :param sp:
    :param str_el:
    :param section_info:
    :param bib_map:
    :param ref_map:
    :return:
    """
    # substitute space characters
    text = re.sub(r'\s+', ' ', str_el)
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
        re.finditer(r'(SECREFU\d+)', text),
    ):
        all_ref_spans.append({
            "start": span.start(),
            "end": span.start() + len(span.group()),
            "ref_id": span.group()
        })

    # assert all align
    for cite_span in all_cite_spans:
        assert text[cite_span['start']:cite_span['end']] == cite_span['ref_id']
    for ref_span in all_ref_spans:
        assert text[ref_span['start']:ref_span['end']] == ref_span['ref_id']

    return Paragraph(
        text=text,
        cite_spans=all_cite_spans,
        ref_spans=all_ref_spans,
        eq_spans=[],
        section=section_info
    )


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
            try:
                formula_mathml = latex2mathml.converter.convert(ftag.texmath.text)
            except Exception:
                formula_mathml = ""
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
            "text": bib_map[span.group()]['num'] if span.group() in bib_map else None,
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
        re.finditer(r'(SECREFU\d+)', text),
    ):
        all_ref_spans.append({
            "start": span.start(),
            "end": span.start() + len(span.group()),
            "text": ref_map[span.group()]['num'] if span.group() in ref_map else None,
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
                "ref_id": span.group()
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


def decompose_tags_before_title(sp: BeautifulSoup):
    """
    decompose all tags before title
    :param sp:
    :return:
    """
    if sp.body.next.name == 'std':
        cld_tags = sp.std.find_all(recursive=False)
        if any([tag.name == 'maketitle' or tag.name == 'title' for tag in cld_tags]):
            for tag in sp.std:
                if type(tag) == bs4.element.Tag:
                    if tag.name != 'maketitle' and tag.name != 'title':
                        tag.decompose()
                    else:
                        break
    elif sp.body.next.name == 'unknown':
        cld_tags = sp.unknown.find_all(recursive=False)
        if any([tag.name == 'maketitle' or tag.name == 'title' for tag in cld_tags]):
            for tag in sp.std:
                if type(tag) == bs4.element.Tag:
                    if tag.name != 'maketitle' and tag.name != 'title':
                        tag.decompose()
                    else:
                        break
    else:
        print(f"Unknown inner tag: {sp.body.next.name}")
        return


def process_metadata(sp: BeautifulSoup, grobid_client: GrobidClient, log_file: str) -> Tuple[str, List]:
    """
    Process metadata section in soup
    :param sp:
    :param grobid_client:
    :param log_file:
    :return:
    """
    title = ""
    authors = []

    if not sp.maketitle and not sp.metadata:
        if sp.title:
            title = sp.title.text
            return title, authors
        else:
            return title, authors
    elif sp.maketitle:
        try:
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
        except AttributeError:
            sp.maketitle.decompose()
            return title, authors
    elif sp.metadata:
        try:
            # process title and authors from metadata
            title = sp.metadata.title.text
            # get authors
            for author in sp.authors:
                for subtag in author:
                    subtag.decompose()
                if author.text.strip():
                    author_parts = author.text.strip().split()
                    authors.append({
                        "first": author_parts[0] if len(author_parts) > 1 else "",
                        "last": author_parts[-1]
                            if author_parts[-1].lower() not in {"jr", "jr.", "iii", "iv", "v"}
                            else author_parts[-2] if len(author_parts) > 1 else author_parts[-1],
                        "middle": author_parts[1:-1],
                        "suffix": "",
                        "affiliation": {},
                        "email": ""
                    })
            sp.metadata.decompose()
        except AttributeError:
            sp.metadata.decompose()
            return title, authors

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
    for bibliography in sp.find_all('bibliography'):
        bib_items = bibliography.find_all('bibitem')
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
    for bibliography in sp.find_all('bibliography'):
        bibliography.decompose()
    return bibkey_map


def get_section_name(sec):
    """
    Get section name from div tag
    :param sec:
    :return:
    """
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


def get_sections_from_div(el: bs4.element.Tag, sp: BeautifulSoup, parent: Optional[str], faux_max: int) -> Dict:
    """
    Process section headers for one div
    :param el:
    :param sp:
    :return:
    """
    sec_map_dict = dict()
    el_ref_id = None

    # process divs with ids
    if el.get('id', None):
        sec_num = el.get('id-text', None)
        if 'cid' in el.get('id'):
            el_ref_id = el.get('id').replace('cid', 'SECREF')
        elif 'uid' in el.get('id'):
            el_ref_id = el.get('id').replace('uid', 'SECREFU')
        else:
            print('Unknown ID type!', el.get('id'))
            raise NotImplementedError
        el['s2orc_id'] = el_ref_id
        sec_map_dict[el_ref_id] = {
            "num": sec_num,
            "text": get_section_name(el),
            "ref_id": el_ref_id,
            "parent": parent
        }
    # process divs without section numbers
    elif el.get('rend') == "nonumber":
        el_ref_id = f'SECREF{faux_max}'
        el['s2orc_id'] = el_ref_id
        sec_map_dict[el_ref_id] = {
            "num": None,
            "text": get_section_name(el),
            "ref_id": el_ref_id,
            "parent": parent
        }

    # process sub elements
    for sub_el in el.find_all(recursive=False):
        if sub_el.name.startswith('div'):
            # add any unspecified keys
            sec_keys = [int(k.strip('SECREF')) for k in sec_map_dict.keys() if k and k.strip('SECREF').isdigit()]
            faux_max = max(sec_keys + [faux_max]) + 1
            sec_map_dict.update(
                get_sections_from_div(sub_el, sp, el_ref_id if el_ref_id else parent, faux_max)
            )
        elif sub_el.name == 'p' or sub_el.name == 'proof':
            if sub_el.get('id', None):
                sec_num = sub_el.get('id-text', sub_el.hi.get('id-text', None))
                if 'cid' in sub_el.get('id'):
                    sub_el_ref_id = sub_el.get('id').replace('cid', 'SECREF')
                elif 'uid' in sub_el.get('id'):
                    sub_el_ref_id = sub_el.get('id').replace('uid', 'SECREFU')
                else:
                    print('Unknown ID type!', sub_el.get('id'))
                    raise NotImplementedError
                sub_el['s2orc_id'] = sub_el_ref_id
                sec_map_dict[el_ref_id] = {
                    "num": sec_num,
                    "text": sub_el.head.text if sub_el.head else sub_el.hi.text if sub_el.hi else "",
                    "ref_id": sub_el_ref_id,
                    "parent": el_ref_id if el_ref_id else parent
                }
    return sec_map_dict


def process_sections_from_text(sp: BeautifulSoup) -> Dict:
    """
    Generate section dict and replace with id tokens
    :param sp:
    :return:
    """
    # initialize
    section_map = dict()
    max_above_1000 = 999

    for div0 in sp.find_all('div0'):
        parent = None
        section_map.update(get_sections_from_div(div0, sp, parent, max_above_1000 + 1))
        # add any unspecified keys
        sec_keys = [int(k.strip('SECREF')) for k in section_map.keys() if k and k.strip('SECREF').isdigit()]
        max_above_1000 = max(sec_keys + [max_above_1000]) + 1

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
            if eq.get('type', None) == 'display':
                if eq.get('id', None):
                    ref_id = eq.get('id').replace('uid', 'EQREF')
                    try:
                        mathml = latex2mathml.converter.convert(eq.texmath.text.strip())
                    except Exception:
                        mathml = ""
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

    # get floats first because they are around figures
    for flt in sp.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'figure':

                # get files
                fig_files = []
                for fig in flt.find_all('figure'):
                    if fig.get('file') and fig.get('extension'):
                        fname = fig.get('file') + '.' + fig.get('extension')
                        fig_files.append(fname)
                    elif fig.get('file'):
                        fname = fig.get('file')
                        fig_files.append(fname)
                    else:
                        for subfig in fig.find_all('subfigure'):
                            if subfig.get('file') and subfig.get('extension'):
                                fig_files.append(subfig.get('file') + '.' + subfig.get('extension'))
                            elif subfig.get('file'):
                                fig_files.append(subfig.get('file'))

                if flt.get('id'):
                    ref_id = flt.get('id').replace('uid', 'FIGREF')
                    # form figmap entry
                    figure_map[ref_id] = {
                        "num": flt.get('id-text', None),
                        "text": None,   # placeholder
                        "uris": fig_files,
                        "ref_id": ref_id
                    }
        except AttributeError:
            print('Attribute error with figure float: ', flt.name)
            continue

    for fig in sp.find_all('figure'):
        try:
            if fig.name and fig.get('id'):
                # normalize figure id
                ref_id = fig.get('id').replace('uid', 'FIGREF')
                # try to get filenames of figures
                fig_files = []
                if fig.get('file') and fig.get('extension'):
                    fname = fig.get('file') + '.' + fig.get('extension')
                    fig_files.append(fname)
                elif fig.get('file'):
                    fig_files.append(fig.get('file'))
                else:
                    for subfig in fig.find_all('subfigure'):
                        if subfig.get('file') and subfig.get('extension'):
                            fig_files.append(subfig.get('file') + '.' + subfig.get('extension'))
                        elif subfig.get('file'):
                            fig_files.append(subfig.get('file'))
                # form figmap entry
                figure_map[ref_id] = {
                    "num": fig.get('id-text', None),
                    "text": None,   # placeholder
                    "uris": fig_files,
                    "ref_id": ref_id
                }
        except AttributeError:
            print('Attribute error with figure: ', fig.name)
            continue

    return figure_map


def process_figures_from_tex(sp: BeautifulSoup, ref_map: Dict) -> Dict:
    """
    Add figure captions to fig_map and decompose
    :param sp:
    :param ref_map:
    :return:
    """
    # process floats first because they are on the outside
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
            print('Attribute error with figure float: ', flt.name)
            continue

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
            print('Attribute error with figure: ', fig.name)
            continue
        fig.decompose()

    return ref_map


def convert_table_to_html(table_lst: List) -> str:
    if not table_lst:
        return ''
    html_str = '<table>'
    for i, row in enumerate(table_lst):
        html_str += '<tr>'
        bottom_border = row.get('bottom-border')
        if i == 0 or bottom_border:
            for cell in row['cells']:
                html_str += f"<th>{cell['text']}</th>"
        else:
            for cell in row['cells']:
                html_str += f"<td>{cell['text']}</td>"
        html_str += '</tr>'
    html_str += '</table>'
    return html_str


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
                "text": text.strip(),
                "latex": latex.strip()
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

    for flt in sp.find_all('float'):
        try:
            if flt.name and flt.get('name') == 'table':
                if flt.get('id'):
                    # normalize table id
                    ref_id = flt.get('id').replace('uid', 'TABREF')
                    # get table content
                    content = extract_table(flt) if keep_table_contents else None
                    html = convert_table_to_html(content) if keep_table_contents else None
                    # form tabmap entry
                    table_map[ref_id] = {
                        "num": flt.get('id-text', None),
                        "text": None,   # placeholder
                        "content": content,
                        "html": html,
                        "ref_id": ref_id
                    }
                    for row in flt.find_all('row'):
                        row.decompose()
        except AttributeError:
            print('Attribute error with table float: ', flt.name)
            continue

    for tab in sp.find_all('table'):
        try:
            # skip inline tables
            if tab.get('rend') == 'inline':
                continue
            # process them
            if tab.name and tab.get('id'):
                # normalize table id
                ref_id = tab.get('id').replace('uid', 'TABREF')
                # get table content
                content = extract_table(tab) if keep_table_contents else None
                html = convert_table_to_html(content) if keep_table_contents else None
                # form tabmap entry
                table_map[ref_id] = {
                    "num": tab.get('id-text', None),
                    "text": None,   # placeholder
                    "content": content,
                    "html": html,
                    "ref_id": ref_id
                }
                for row in tab.find_all('row'):
                    row.decompose()
        except AttributeError:
            print('Attribute error with table: ', tab.name)
            continue

    return table_map


def process_tables_from_tex(sp: BeautifulSoup, ref_map: Dict) -> Dict:
    """
    Generate table dict and replace with id tokens
    :param sp:
    :param ref_map:
    :return:
    """
    # process floats first because they are on the outside
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
            print('Attribute error with table float: ', flt.name)
            continue

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
            print('Attribute error with table: ', tab.name)
            continue
        tab.decompose()

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


def collapse_formatting_tags(sp: BeautifulSoup):
    """
    Collapse formatting tags like <hi>
    :param sp:
    :return:
    """
    for hi in sp.find_all('hi'):
        hi.replace_with(f' {sp.new_string(hi.text.strip())} ')


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
        if sp.std:
            p_tags = [tag for tag in sp.std if tag.name == 'p' and not tag.get('s2orc_id', None)]
        elif sp.unknown:
            p_tags = [tag for tag in sp.unknown if tag.name == 'p' and not tag.get('s2orc_id', None)]
        else:
            p_tags = None
        if p_tags:
            for p in p_tags:
                abstract_text.append(
                    process_paragraph(sp, p, [(None, "Abstract")], bib_map, ref_map)
                )
                p.decompose()
    return [para.__dict__ for para in abstract_text]


def build_section_list(sec_id: str, ref_map: Dict) -> List[Tuple]:
    """
    Build list of sections from reference map from sec_id using parent entry recursively
    :param sec_id:
    :param ref_map:
    :return:
    """
    if not sec_id:
        return []
    elif sec_id not in ref_map:
        return []
    else:
        sec_entry = [(ref_map[sec_id]['num'], ref_map[sec_id]['text'])]
        if ref_map[sec_id]['parent'] == sec_id:
            return sec_entry
        else:
            return build_section_list(ref_map[sec_id]['parent'], ref_map) + sec_entry


def get_seclist_for_el(el: bs4.element.Tag, ref_map: Dict, default_seclist: List) -> List[Tuple]:
    """
    Build sec_list for tag
    :param el:
    :param ref_map:
    :param default_seclist:
    :return:
    """
    if type(el) == NavigableString:
        return default_seclist
    sec_id = el.get('s2orc_id', None)
    if sec_id:
        return build_section_list(sec_id, ref_map)
    else:
        return default_seclist


def process_div(tag: bs4.element.Tag, secs: List, sp: BeautifulSoup, bib_map: Dict, ref_map: Dict) -> List[Dict]:
    """
    Process div recursively
    :param tag:
    :param secs:
    :param sp:
    :param bib_map:
    :param ref_map:
    :return:
    """
    # iterate through children of this tag
    body_text = []

    # navigable strings
    if type(tag) == NavigableString:
        return []
    # skip these tags
    elif tag.name in SKIP_TAGS:
        return []
    # process normal tags
    elif tag.name in TEXT_TAGS:
        if tag.text:
            body_text.append(process_paragraph(sp, tag, secs, bib_map, ref_map))
    # process lists
    elif tag.name == 'list':
        if tag.text:
            body_text += process_list_el(sp, tag, secs, bib_map, ref_map)
    # process formula
    elif tag.name == 'formula':
        replace_item = sp.new_tag('p')
        tag_copy = copy.copy(tag)
        tag_copy['type'] = 'inline'
        replace_item.insert(0, tag_copy)
        tag.replace_with(replace_item)
        if tag.text:
            body_text.append(process_paragraph(sp, tag, secs, bib_map, ref_map))
    # process divs
    elif tag.name.startswith('div'):
        for el in tag:
            # process tags
            if type(el) == bs4.element.Tag:
                el_sec_list = get_seclist_for_el(el, ref_map, secs)
                body_text += process_div(el, el_sec_list, sp, bib_map, ref_map)
    # unknown tag type, skip for now
    else:
        print(f'Unknown tag type: {tag.name}')
        return []

    return body_text


def process_body_text_from_tex(sp: BeautifulSoup, bib_map: Dict, ref_map: Dict) -> List[Dict]:
    """
    Parse body text from tag recursively
    :param sp:
    :param bib_map:
    :param ref_map:
    :return:
    """
    body_text = []
    for tag in sp.body:
        # skip navigable string
        if type(tag) == NavigableString:
            continue
        else:
            sec_list = get_seclist_for_el(tag, ref_map, [])
            for cld in tag:
                # skip navigable string
                if type(tag) == NavigableString:
                    continue
                else:
                    sec_list = get_seclist_for_el(cld, ref_map, sec_list)
                    if type(cld) == bs4.element.Tag:
                        body_text += process_div(cld, sec_list, sp, bib_map, ref_map)

    # decompose everything
    sp.body.decompose()

    return [para.__dict__ for para in body_text]


def convert_xml_to_s2orc(
        sp: BeautifulSoup, file_id: str, year_str: str, log_file: str, grobid_config: Optional[Dict]=None
) -> Paper:
    """
    Convert a bunch of xml to gorc format
    :param sp:
    :param file_id:
    :param year_str:
    :param log_file:
    :param grobid_config:
    :return:
    """
    # create grobid client
    client = GrobidClient(grobid_config)

    # TODO: not sure why but have to run twice
    decompose_tags_before_title(sp)
    decompose_tags_before_title(sp)

    # process maketitle info
    title, authors = process_metadata(sp, client, log_file)

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

    # collapse all hi tags
    collapse_formatting_tags(sp)

    # process abstract if possible
    abstract = process_abstract_from_tex(sp, bibkey_map, refkey_map)

    # process body text
    body_text = process_body_text_from_tex(sp, bibkey_map, refkey_map)

    # skip if no body text parsed
    if not body_text:
        with open(log_file, 'a+') as body_f:
            body_f.write(f'{file_id},warn_no_body\n')

    metadata = {
        "title": title,
        "authors": authors,
        "year": year_str,
        "venue": "",
        "identifiers": {
            "arxiv_id": file_id
        }
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


def convert_latex_xml_to_s2orc_json(xml_fpath: str, log_dir: str, grobid_config: Optional[Dict]=None) -> Paper:
    """
    :param xml_fpath:
    :param log_dir:
    :param grobid_config:
    :return:
    """
    assert os.path.exists(xml_fpath)

    # get file id
    file_id = str(os.path.splitext(xml_fpath)[0]).split('/')[-1]

    # try to get year from file name
    year = file_id.split('.')[0][:2]
    if year.isdigit():
        year = int(year)
        if year < 40:
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
            paper = convert_xml_to_s2orc(soup, file_id, year, log_file, grobid_config=grobid_config)
            return paper
        except UnicodeDecodeError:
            with open(log_file, 'a+') as log_f:
                log_f.write(f'{file_id},err_unicode_decode\n')
            raise UnicodeDecodeError
