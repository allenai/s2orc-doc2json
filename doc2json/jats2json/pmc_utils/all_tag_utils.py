from typing import Dict, List, Callable

import re
import itertools

from bs4 import BeautifulSoup

START_TOKENS = {"#!start#", "@!start@", "&!start&"}
SEP_TOKENS = {"#!sep#"}
END_TOKENS = {"#!end#", "@!end@", "&!end&"}
ALL_TOKENS = START_TOKENS | SEP_TOKENS | END_TOKENS


def replace_xref_with_string_placeholders(soup_tag, soup):
    # replace all xref tags with string placeholders
    for xref_tag in soup_tag.find_all("xref"):
        rid = xref_tag['rid'] if 'rid' in xref_tag.attrs else None
        ref_type = xref_tag['ref-type'] if 'ref-type' in xref_tag.attrs else None
        xref_tag.replace_with(
            soup.new_string(
                f"#!start#{xref_tag.text}#!sep#{rid}#!sep#{ref_type}#!end#"
            )
        )


def replace_sup_sub_tags_with_string_placeholders(soup_tag, soup):
    # replace all sup/sub tags with string placeholders
    for sup_tag in soup_tag.find_all("sup"):
        sup_tag.replace_with(soup.new_string(f"@!start@{sup_tag.text}@!end@"))
    for sub_tag in soup_tag.find_all("sub"):
        sub_tag.replace_with(soup.new_string(f"&!start&{sub_tag.text}&!end&"))


def recurse_parse_section(
    sec_tag,
    # suppl_blobs: Dict
) -> List[Dict]:
    """Recursive function for getting paragraph blobs to look like
        {
            'text': ...,
            ...,
            'section': SUBSUBSECTION_NAME :: SUBSECTION_NAME :: SECTION_NAME
        }
    """
    subsections = sec_tag.find_all("sec", recursive=False)
    if not subsections:
        return parse_all_paragraphs_in_section(
            sec_tag=sec_tag
        )  # , suppl_blobs=suppl_blobs)
    else:
        outputs = []
        for child in subsections:
            child_blobs = recurse_parse_section(
                sec_tag=child
            )  # , suppl_blobs=suppl_blobs)
            for blob in child_blobs:
                # PMC373254 - process blob['section'] to remove any span markers left in there
                for t in ALL_TOKENS:
                    blob['section'] = blob['section'].replace(t, '')
                blob["section"] = blob["section"] + " :: " + sec_tag.find("title").text
            outputs.extend(child_blobs)
        return outputs


def _reduce_args(stack: List, end_token: str) -> List[List]:
    """Helper function for `_parse_all_paragraphs_in_section`.
    
    Pop arguments for the xref off the top of the stack and return a list of argument lists,
    where the outer lists represent groups divided by separators."""
    start_token = end_token.replace('end', 'start')
    sep_token = end_token.replace('end', 'sep')
    args = [[]]
    while True:
        token = stack.pop()
        if token == start_token:
            return args
        elif token == sep_token:
            args.insert(0, [])
        else:
            args[0].insert(0, token)


def _add_spans(
    end_token: str,
    start_pos: int,
    text: str,
    ref_id,
    ref_type,
    cite_spans: List,
    fig_spans: List,
    table_spans: List,
    sup_spans: List,
    sub_spans: List,
):
    """Helper function used by `_parse_all_paragraphs_in_section`."""
    if end_token.startswith("#"):  # process xref
        blob = {
            "start": start_pos,
            "end": start_pos + len(text),
            "mention": text,
            "ref_id": ref_id,
        }
        if ref_type == "bibr":
            cite_spans.append(blob)
        elif ref_type == "fig":
            fig_spans.append(blob)
        elif ref_type == "table":
            table_spans.append(blob)

    else:
        blob = {
            "start": start_pos,
            "end": start_pos + len(text),
            "mention": text,
        }
        if end_token.startswith("@"):
            sup_spans.append(blob)
        else:
            assert end_token.startswith("&")
            sub_spans.append(blob)


def get_latex_from_formula(
    formula_tag
):
    if formula_tag.find('tex-math'):
        latex_text = formula_tag.find('tex-math').text
        match = re.search(r'\\begin\{document\}(.+)\\end\{document\}', latex_text)
        if match:
            return match.group(1).strip('$')
    return None


def get_mathml_from_formula(
    formula_tag
):
    if formula_tag.find('mml:math'):
        return str(formula_tag.find('mml:math'))
    return None


def parse_formulas(
    para_el,
    sp,
    replace
):
    # sub and get corresponding spans of inline formulas
    formula_dict = dict()
    eq_ind = 0
    for ftag in para_el.find_all('inline-formula'):
        try:
            formula_key = f'INLINEFORM{eq_ind}'
            eq_ind += 1
            try:
                formula_text = ftag.find('mml:math').text
            except:
                if 'begin{document}' not in ftag.text:
                    formula_text = ftag.text
                else:
                    formula_text = "FORMULA"
            formula_latex = get_latex_from_formula(ftag)
            formula_mathml = get_mathml_from_formula(ftag)
            if not formula_mathml and formula_latex:
                formula_mathml = latex2mathml.converter.convert(formula_latex)
            formula_dict[formula_key] = (formula_text, formula_latex, formula_mathml, ftag.get('id'))
            if replace:
                ftag.replace_with(sp.new_string(f" {formula_key} "))
            else:
                # replace with mathml text if available
                if formula_text != 'FORMULA':
                    ftag.replace_with(sp.new_string(f" {formula_text} "))
        except AttributeError:
            continue

    return formula_dict


def parse_all_paragraphs_in_section(
    sec_tag,
    par_to_text: Callable = None,
    replace_formula=True
) -> List[Dict]:
    """Internal function. Assumes section has no nested tags
    `par_to_text` is an optional function that converts the `par` tag into a string.  by default, calls `par_tag.text`.
    """
    outputs = []
    sp = BeautifulSoup('', 'lxml')
    for par_tag in sec_tag.find_all("p", recursive=True):
        cite_spans = []
        fig_spans = []
        table_spans = []
        # suppl_spans = []
        sup_spans = []
        sub_spans = []
        eq_spans = []

        if par_tag.find('display-formula'):
            raise NotImplementedError('Display formula!')

        if par_tag.find('formula'):
            raise NotImplementedError('Formula!')

        formula_dict = parse_formulas(par_tag, sp, replace_formula)

        par_text = par_to_text(par_tag) if par_to_text else par_tag.text
        par_text = re.sub(
            r"[^\S\n\t]", " ", par_text
        )  # replaces whitespace but not newline or tab
        par_text = re.sub(
            r"  ", " ", par_text
        )  # replaces two spaces w/ one

        # Tokenize the text into normal text and special placeholder tokens.
        pattern = r"(#!start#)|(#!sep#)|(#!end#)|(@!start@)|(@!end@)|(&!start&)|(&!end&)"
        tokens = [tok for tok in re.split(pattern, par_text) if tok]

        # To handle nested structures, use a shift-reduce algorithm to consume the text. Placeholder tags are merged away, and related spans are registered.
        stack = []
        full_text = []
        pos = 0
        disable_count = False
        for token in tokens:
            if token in START_TOKENS:
                stack.append(token)
                stack.append(pos)
                stack.append(token.replace('start', 'sep'))
            elif token in SEP_TOKENS:
                assert stack
                stack.append(token)
                disable_count = True
            elif token in END_TOKENS:
                assert stack
                disable_count = False
                args = _reduce_args(stack, token)
                start_pos = args[0][0]
                text = "".join(args[1])
                assert len(args) == 2 or len(args) == 4
                if len(args) == 2:
                    ref_id, ref_type = None, None
                elif len(args) == 4:
                    ref_id = args[2] and args[2][0]
                    ref_type = args[3] and args[3][0]
                stack.append(text)
                _add_spans(
                    token,
                    start_pos,
                    text,
                    ref_id,
                    ref_type,
                    cite_spans,
                    fig_spans,
                    table_spans,
                    sup_spans,
                    sub_spans,
                )
            else:  # just normal text
                stack.append(token)
                if not disable_count:  # metadata appearing after a separator
                    full_text.append(token)
                    pos += len(token)

        full_text = "".join(full_text)
        assert pos == len(full_text)

        title = sec_tag.find("title")
        title = title.text if title else ""

        # get all equation spans
        eq_spans = []
        for span in itertools.chain(
                re.finditer(r'(INLINEFORM\d+)', full_text),
                re.finditer(r'(DISPLAYFORM\d+)', full_text)
        ):
            try:
                matching_formula = formula_dict[span.group()]
                eq_spans.append({
                    "start": span.start(),
                    "end": span.start() + len(span.group()),
                    "text": matching_formula[0],
                    "latex": matching_formula[1],
                    "mathml": matching_formula[2],
                    "ref_id": span.group()
                })
            except KeyError:
                continue

        outputs.append(
            {
                "text": full_text,
                'cite_spans': cite_spans,
                'fig_spans': fig_spans,
                'table_spans': table_spans,
                # 'suppl_spans': suppl_spans,
                'sup_spans': sup_spans,
                'sub_spans': sub_spans,
                'eq_spans': eq_spans,
                "section": title,
            }
        )
    return outputs
