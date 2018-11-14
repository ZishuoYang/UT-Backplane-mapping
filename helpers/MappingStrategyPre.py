#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Nov 14, 2018 at 10:51 AM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

strategy_yaml_filename = input_dir / Path('mapping_strategy.yml')
strategy_tex_filename  = output_dir / Path('mapping_strategy.tex')


###########
# Helpers #
###########

header = '''\\documentclass[12pt]{article}

\\usepackage[margin=0.5in,landscape]{geometry}

\\usepackage{tabularx,booktab,diagbox}

\\usepackage{bigstrut}
\\setlength\\bigstrutjot{3pt}

\\renewcommand{\\arraystretch}{1.2}

\\begin{document}

\\thispagestyle{empty}
\\begin{table}[ht]
\\begin{tabularx}{\\textwidth}{X|X|X|X|X|X|X|X|X|X|X|X}
    \\hline
    \\diagbox[innerwidth=3.64em]{PT}{DCB}
'''

footer = '''\\end{tabularx}
\\end{table}

\\end{document}'''

table_line_end = ' \\bigstrut \\\\ \\hline \n'


def collect_JD_terms(d):
    return {k: d[k] for k in d.keys() if 'JD' in k}


###################################
# Read from mapping strategy yaml #
###################################

with open(strategy_yaml_filename) as yaml_file:
    strategy_dict = yaml.safe_load(yaml_file)


#####################
# Generate tex file #
#####################

with open(strategy_tex_filename, 'w') as tex_file:
    tex_file.write(header)

    # Fill out the remainder of the header
    jd_dict = collect_JD_terms(strategy_dict)
    tex_file.write('    ')

    for jd in jd_dict.keys():
        tex_file.write('& ')
        tex_file.write(jd)
        if jd_dict[jd]['depopulation']:
            tex_file.write('$^{depop}$')
        tex_file.write(' ')

    tex_file.write(table_line_end)

    tex_file.write(footer)
