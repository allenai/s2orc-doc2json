"""
Many of the REGEX expressions and pipeline in this set of utilities are borrowed or extended from
the unarXive project: https://github.com/IllDepence/unarXive

Modifications have been made to better identify the primary latex file and expand all other latex
files into the main file. Latexpand and tralics options have also been changed.
"""
import chardet
import magic
import os
import re
import glob
import subprocess
import tempfile

MAIN_TEX_PATT = re.compile(r'(\\begin\s*\{\s*document\s*\})', re.I)
# ^ with capturing parentheses so that the pattern can be used for splitting
PDF_EXT_PATT = re.compile(r'^\.pdf$', re.I)
GZ_EXT_PATT = re.compile(r'^\.gz$', re.I)
TEX_EXT_PATT = re.compile(r'^\.tex$', re.I)
NON_TEXT_PATT = re.compile(r'^\.(pdf|eps|jpg|png|gif)$', re.I)
BBL_SIGN = '\\bibitem'
# natbib fix
PRE_FIX_NATBIB = True
NATBIB_PATT = re.compile((r'\\cite(t|p|alt|alp|author|year|yearpar)\s*?\*?\s*?'
                           '(\[[^\]]*?\]\s*?)*?\s*?\*?\s*?\{([^\}]+?)\}'),
                         re.I)
# bibitem option fix
PRE_FIX_BIBOPT = True
BIBOPT_PATT = re.compile(r'\\bibitem\s*?\[[^]]*?\]', re.I|re.M)

# ↑ above two solve most tralics problems; except for mnras style bibitems
# (https://ctan.org/pkg/mnras)

# agressive math pre-removal
PRE_FILTER_MATH = False
FILTER_PATTS = []
for env in ['equation', 'displaymath', 'array', 'eqnarray', 'align', 'gather',
            'multline', 'flalign', 'alignat']:
    s = r'\\begin\{{{0}[*]?\}}.+?\\end\{{{0}\}}'.format(env)
    patt = re.compile(s, re.I | re.M | re.S)
    FILTER_PATTS.append(patt)
FILTER_PATTS.append(re.compile(r'\$\$.+?\$\$', re.S))
FILTER_PATTS.append(re.compile(r'\$.+?\$', re.S))
FILTER_PATTS.append(re.compile(r'\\\(.+?\\\)', re.S))
FILTER_PATTS.append(re.compile(r'\\\[.+?\\\]', re.S))


def read_file(path):
    try:
        with open(path) as f:
            cntnt = f.read()
    except UnicodeDecodeError:
        blob = open(path, 'rb').read()
        m = magic.Magic(mime_encoding=True)
        encoding = m.from_buffer(blob)
        try:
            cntnt = blob.decode(encoding)
        except (UnicodeDecodeError, LookupError) as e:
            encoding = chardet.detect(blob)['encoding']
            if encoding:
                try:
                    cntnt = blob.decode(encoding, errors='replace')
                except:
                    return ''
            else:
                return ''
    return cntnt


def remove_math(latex_str):
    parts = re.split(MAIN_TEX_PATT, latex_str, maxsplit=1)
    for patt in FILTER_PATTS:
         parts[2] = re.sub(patt, '', parts[2])
    return ''.join(parts)


def normalize(path, out_dir, write_logs=True):
    """
    Normalize an arXiv file
    Adapted from https://github.com/IllDepence/unarXive
        with modifications

    Identifies the primary *.tex file, the bibliography file,
    and expands other tex files and the bibliography into the
    main tex file
    """
    def log(msg):
        if write_logs:
            with open(os.path.join(out_dir, 'log.txt'), 'a') as f:
                f.write('{}\n'.format(msg))

    # break path
    _, fn = os.path.split(path.strip('/'))

    # identify main tex file
    main_tex_path = None
    ignored_names = []

    # check .tex files first
    for tfn in os.listdir(path):

        if not TEX_EXT_PATT.match(os.path.splitext(tfn)[1]):
            ignored_names.append(tfn)
            continue

        try:
            cntnt = read_file(os.path.join(path, tfn))
        except:
            continue

        if re.search(MAIN_TEX_PATT, cntnt) is not None:
            main_tex_path = tfn

    # try other files
    if main_tex_path is None:
        for tfn in ignored_names:
            if NON_TEXT_PATT.match(os.path.splitext(tfn)[1]):
                continue
            try:
                cntnt = read_file(os.path.join(path, tfn))
                if re.search(MAIN_TEX_PATT, cntnt) is not None:
                    main_tex_path = tfn
            except:
                continue

    # give up
    if main_tex_path is None:
        log(('couldn\'t find main tex file in dump archive {}'
             '').format(fn))

    # flatten to single tex file and save
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        temp_tex_fn = os.path.join(tmp_dir_path, f'{fn}.tex')

        # find bbl file
        main_tex_fn = os.path.join(path, main_tex_path)
        bbl_files = glob.glob(os.path.join(path, '*.bbl'))

        if bbl_files:
            latexpand_args = ['latexpand',
                              '--expand-bbl',
                              os.path.split(bbl_files[0])[1],
                              main_tex_path,
                              '--output',
                              temp_tex_fn]
        else:
            latexpand_args = ['latexpand',
                              main_tex_path,
                              '--output',
                              temp_tex_fn]

        # run latexpand
        with open(os.path.join(out_dir, 'log_latexpand.txt'), 'a+') as err:
            subprocess.run(latexpand_args, stderr=err, cwd=path)

        # re-read and write to ensure utf-8 b/c latexpand doesn't
        # behave
        new_tex_fn = os.path.join(out_dir, f'{fn}.tex')
        cntnt = read_file(temp_tex_fn)
        if PRE_FIX_NATBIB:
            cntnt = NATBIB_PATT.sub(r'\\cite{\3}', cntnt)
        if PRE_FIX_BIBOPT:
            cntnt = BIBOPT_PATT.sub(r'\\bibitem', cntnt)
        if PRE_FILTER_MATH:
            cntnt = remove_math(cntnt)
        with open(new_tex_fn, mode='w', encoding='utf-8') as f:
            f.write(cntnt)


def latex_to_xml(tex_file: str, out_dir: str, out_file: str, err_file: str, log_file: str):
    """
    Convert expanded latex file to XML using tralics
    :param tex_file:
    :param out_dir:
    :param out_file:
    :param err_file:
    :param log_file:
    :return:
    """
    with open(os.devnull, 'w') as devnull, \
            open(err_file, 'a+') as err_f, \
            open(log_file, 'a+') as skip_f:
        # run tralics
        tralics_args = ['tralics',
                        '-silent',
                        '-noxmlerror',
                        '-utf8',
                        '-oe8',
                        '-entnames=false',
                        '-nomathml',
                        f'-output_dir={out_dir}',
                        tex_file]
        try:
            subprocess.run(tralics_args, stdout=devnull, stderr=err_f, timeout=5)
        except subprocess.TimeoutExpired:
            skip_f.write(f'{tex_file}\n')

        # if no output, skip
        if not os.path.exists(out_file):
            skip_f.write(f'{tex_file}\n')

    if os.path.exists(out_file):
        return out_file
