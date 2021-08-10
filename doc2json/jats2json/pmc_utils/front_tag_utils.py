"""

Functions for parsing specific `front_tag` soup tags

"""

from typing import Dict, List, Optional

from collections import Counter

import re


from doc2json.jats2json.pmc_utils.all_tag_utils import recurse_parse_section, parse_all_paragraphs_in_section, \
    replace_sup_sub_tags_with_string_placeholders, replace_xref_with_string_placeholders


class NoAuthorNamesError(Exception):
    """Known papers that trigger:
        - PMC3462967
    """
    pass


def parse_journal_id_tag(front_tag) -> str:
    """
    front_tag.find_all('journal-id') returns:
        [
            <journal-id journal-id-type="nlm-ta">Neurosci J</journal-id>,
            <journal-id journal-id-type="iso-abbrev">Neurosci J</journal-id>,
            <journal-id journal-id-type="publisher-id">NEUROSCIENCE</journal-id>
        ]
        [
            <journal-id journal-id-type="nlm-ta">BMC Biochem</journal-id>
            <journal-id journal-id-type="iso-abbrev">BMC Biochem</journal-id>
        ]
    """
    c = Counter()
    for tag in front_tag.find_all('journal-id'):
        c[tag.text] += 1
        tag.decompose()
    journal_id, n = c.most_common(1)[0]
    return journal_id


def parse_journal_name_tag(front_tag) -> str:
    """
    Examples:
        # Paper 1
        <journal-title-group>
            <journal-title>BMC Biochemistry</journal-title>
        </journal-title-group>
        # Paper 2
        <journal-title-group>
            <journal-title>Neuroscience Journal</journal-title>
        </journal-title-group>

    But not all titles are contained within a `journal-title-group`.  See PMC1079901
        <journal-meta>
            <journal-id journal-id-type="nlm-ta">
                Biomed Eng Online
            </journal-id>
            <journal-title>
                BioMedical Engineering OnLine
            </journal-title>
        ...
    """
    if len(front_tag.find_all('journal-title')) > 1:
        raise Exception('Multiple journal titles?!')
    return front_tag.find('journal-title').extract().text


def parse_pubmed_id_tag(front_tag) -> Optional[str]:
    """Not every PMC paper has a PMID """
    pmid_tag = front_tag.find('article-id', {'pub-id-type': 'pmid'})
    if pmid_tag is None:
        return None
    else:
        return pmid_tag.extract().text


def parse_pmc_id_tag(front_tag) -> str:
    return f"PMC{front_tag.find('article-id', {'pub-id-type': 'pmc'}).extract().text}"


def parse_doi_tag(front_tag) -> Optional[str]:
    """Not all papers have a DOI"""
    doi_tag = front_tag.find('article-id', {'pub-id-type': 'doi'})
    if doi_tag is not None:
        return doi_tag.extract().text
    else:
        return None


def parse_title_tag(front_tag) -> str:
    """
    Examples:
        # Paper 1
        <title-group>
            <article-title>Role of the highly conserved G68 residue in the yeast phosphorelay protein Ypd1: implications for interactions between histidine phosphotransfer (HPt) and response regulator proteins</article-title>
        </title-group>
        # Paper 2
        <title-group>
            <article-title>Association of Strength and Physical Functions in People with Parkinson's Disease</article-title>
        </title-group>

    Want to restrict to `title-group` because sometimes title shows up in <notes> under self-citation
    """
    title_group = front_tag.find('title-group').extract()
    if len(title_group.find_all('article-title')) > 1:
        raise Exception('Multiple article titles?!')
    return title_group.find('article-title').text


def parse_category_tag(front_tag) -> List[str]:
    """
    Examples:
        # Paper 1
        <article-categories>
            <subj-group subj-group-type="heading">
                <subject>Research Article</subject>
            </subj-group>
        </article-categories>
        # Paper 2
        <article-categories>
            <subj-group subj-group-type="heading">
                <subject>Research Article</subject>
            </subj-group>
        </article-categories>
    """
    if len(front_tag.find_all('subj-group')) > 1 or len(front_tag.find_all('subject')) > 1:
        raise Exception('Multiple categories?!')
    article_categories = front_tag.find('article-categories').extract()
    return article_categories.find('subject').text


def parse_date_tag(front_tag) -> Dict:
    """
    Two sets of tags contain dates:
        <pub-date pub-type="collection">
            <year>2018</year>
        </pub-date>
        <pub-date pub-type="epub">
            <day>12</day>
            <month>12</month>
            <year>2018</year>
        </pub-date>
    And:
        <history>
            <date date-type="received">
                <day>15</day>
                <month>10</month>
                <year>2018</year>
            </date>
            <date date-type="rev-recd">
                <day>20</day>
                <month>11</month>
                <year>2018</year>
            </date>
            <date date-type="accepted">
                <day>26</day>
                <month>11</month>
                <year>2018</year>
            </date>
        </history>

    PMC2557072 has `date` tag with no `day`, only `year` and `month`
    """
    out = {}
    for pub_date in front_tag.find_all('pub-date'):
        year = pub_date.find('year')
        month = pub_date.find('month')
        day = pub_date.find('day')
        out[pub_date.get('pub-type', 'MISSING_PUB_TYPE')] = '-'.join([tag.text for tag in [year, month, day] if tag is not None])
        pub_date.decompose()
    for date in front_tag.find_all('date'):
        year = date.find('year')
        month = date.find('month')
        day = date.find('day')
        out[date.get('date-type', 'MISSING_DATE_TYPE')] = '-'.join([tag.text for tag in [year, month, day] if tag is not None])
        date.decompose()
    return out


def parse_funding_groups(front_tag) -> List[str]:
    outs = []
    for tag in front_tag.find_all():

        # AND statement skips cases where the two tag types nest within each other; we only process the inner one
        if (tag.name == 'funding-source' or tag.name == 'funding-statement') and tag.find('funding-source') is None and tag.find('funding-statement') is None:

            out = {
                'name': None,
                'doi': None,
                'notes': None,
                # 'raw': str(tag)       # for debugging
            }

            # handle institution
            institution_id_tag = tag.find('institution-id')
            if institution_id_tag:
                out['doi'] = institution_id_tag.extract().text.replace('http://dx.doi.org/', '')
            institution_tag = tag.find('institution')
            if institution_tag:
                out['name'] = tag.find('institution').extract().text

            # handle named content
            funder_name_tag = tag.find('named-content', {'content-type': 'funder-name'})
            if funder_name_tag:
                out['name'] = funder_name_tag.extract().text

            funder_id_tag = tag.find('named-content', {'content-type': 'funder-identifier'})
            if funder_id_tag:
                out['doi'] = funder_id_tag.extract().text.replace('http://dx.doi.org/', '')

            # handle urls
            if tag.get('xlink:href'):
                out['doi'] = tag['xlink:href']

            # fix DOIs with URLs in them
            if out['doi']:
                match = re.search(r'http(s?)://dx.doi.org/(.+)', out['doi'])
                if match:
                    out['doi'] = match.group(2)

            # remainder text is either a name or a full statement
            text = tag.text
            if tag.name == 'funding-statement' or ('fund' in text or 'support' in text or 'provide' in text):
                out['notes'] = text
            else:
                # what if something already in 'name'?  observed it's typically empty string; so ignore.
                if not out['name']:
                    out['name'] = text
            
            # if DOI link is in the name, remove it and parse (PMC5407128)
            if out['name'] and not out['doi']:
                pattern = r'\s*http(s?)://dx.doi.org/(.+)$'
                match = re.search(pattern, out['name'])
                if match:
                    out['doi'] = match.group(2)
                    out['name'] = re.sub(pattern, r'', out['name'])

            outs.append(out)
    return outs


# TODO: didnt want to handle <collab> group names; seemed rare and inconsistent; focus on <contrib> with <name> and <aff>
def parse_authors(front_tag) -> List[Dict]:
    authors = []
    for contrib_tag in front_tag.find_all('contrib'):

        # skip nesting; just process children (individual authors)
        if contrib_tag.find_all('contrib'):
            continue

        # skip contribs without a name; these should be ones that consist of <collab> tag
        if contrib_tag.find('name') is None:
            continue

        # corresponding tag
        if (contrib_tag.get('corresp') == 'yes') or (contrib_tag.find('xref', {'ref-type': 'corresp'})):
            is_corresp = True
        else:
            is_corresp = False

        # orcid ID is sometimes a URL or just a number.  standardize as hyphenized number.
        if contrib_tag.find('contrib-id'):
            orcid_id = contrib_tag.find('contrib-id').text
            match = re.search(r'http(s?)://orcid.org/(.+)', orcid_id)
            if match:
                orcid_id = match.group(2)
            # A very small number of articles have ID type CATS, which we don't handle. For example:
            #   /disk2/gorpus/20200101/pmc/Change/PMC6176774.nxml
            if len(orcid_id) != 19:
                orcid_id = None
        else:
            orcid_id = None

        # Email may or may not be present.
        email = contrib_tag.find('email')
        email = email.text if email else None

        # Get the name info for the author.
        name_info = {name_tag.name: name_tag.text for name_tag in contrib_tag.find('name').find_all()}
        # TODO: PMC3462967 is an Erratum. It does not have ['given-names'].  not sure we care about those, so try-catch for now
        try:
            given_names = name_info['given-names'].split(' ')
        except KeyError as e:
            raise NoAuthorNamesError

        authors.append({
            'first': given_names[0] if given_names else None,
            'middle': given_names[1:] if given_names else None,
            'last': name_info['surname'],
            'suffix': name_info.get('suffix', ''),
            'email': email,
            'affiliation_ids': [xref_tag.get('rid') for xref_tag in contrib_tag.find_all('xref', {'ref-type': 'aff'})],
            'corresponding': is_corresp,
            'orcid': orcid_id
        })

        # authors.append(str(contrib_tag.extract()))
    return authors


def parse_affiliations(front_tag) -> List[Dict]:
    """
    Sometimes affiliations is nested within '<contrib-group>' along with
    authors.  Sometimes, they're not and listed outside as multiple tags.

    Not all <aff> have IDs.  For example:
        <aff>St. Paul, Minnesota</aff>
    """
    outs = []
    for aff_tag in front_tag.find_all('aff'):
        if aff_tag.find('label'):                   # get rid of unused markers so `.text` is cleaner
            aff_tag.find('label').decompose()
        if aff_tag.find('sup'):
            aff_tag.find('sup').decompose()         # same treatment as label

        aff_id = aff_tag.get('id')

        # it looks like we want to go to the full affiliation surface form without worrying about all possible handlings of <named-content> and other fields
        # BUT, we do want to keep ISNI and GRID IDs when they occur.  They seem to occur typically within <institution-wrap>
        # so let's handle those if they exist; safely decompose the tags (because they dont contribute to surface form); then grab remaining affiliation surface form

        # implicit in this approach is that we dont need to actually handle <institution-wrap> tags because only one per affiliation
        if len(aff_tag.find_all('institution-wrap')) > 1:
            import pdb; pdb.set_trace()
        id_type_to_id = {}
        for institution_id_tag in aff_tag.find_all('institution-id'):
            id_type_to_id[institution_id_tag['institution-id-type']] = institution_id_tag.text
            institution_id_tag.decompose()

        # TODO: processing of text:  there are a lot of random newline chars (cuz XML preserves page layout)
        # --> replace them with whitespace if there's preceding punctuation char
        # --> otherwise, replace them with comma
        text = aff_tag.text

        outs.append({
            'id': aff_id,
            'other_ids': id_type_to_id,
            'text': text
        })

    return outs


def parse_abstract_tag(front_tag, soup) -> List[Dict]:
    """Not every paper has an abstract

    Furthermore, note very abstract is structured into sections.
    Some abstracts (see PMC1914226) look like:
        <abstract>
            <p> ... </p>
            <p> ... </p>
        </abstract>
    """
    # TODO: are there cases where <abstract> text <p> text </> </abstract> ?
    abstract: List[Dict] = []
    if front_tag.find('abstract'):
        abstract_tag = front_tag.find('abstract').extract()

        # replace all xref tags with string placeholders
        replace_xref_with_string_placeholders(soup_tag=abstract_tag, soup=soup)

        # replace all sup/sub tags with string placeholders
        replace_sup_sub_tags_with_string_placeholders(soup_tag=abstract_tag, soup=soup)

        if abstract_tag.find('sec'):
            all_par_blobs = []
            for sec_tag in abstract_tag.find_all('sec', recursive=False):
                par_blobs = recurse_parse_section(sec_tag=sec_tag)
                all_par_blobs.extend(par_blobs)
        else:
            all_par_blobs = parse_all_paragraphs_in_section(sec_tag=abstract_tag)
            for par_blob in all_par_blobs:
                # these 'sections' typically show up as empty string
                par_blob['section'] = 'Abstract'
                abstract.append(par_blob)
    return abstract