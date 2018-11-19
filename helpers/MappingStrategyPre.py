#!/usr/bin/env python
#
# License: MIT
# Last Change: Mon Nov 19, 2018 at 02:24 PM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

from pyUTM.selection import Selector, Rule

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

strategy_yaml_filename = input_dir / Path('mapping_strategy.yml')
strategy_tex_filename  = output_dir / Path('mapping_strategy.tex')


###########
# Helpers #
###########

header = '''\\documentclass[12pt]{article}

\\usepackage[margin=0.5in,landscape]{geometry}

\\usepackage{tabularx,diagbox,xcolor,soul}

\\renewcommand{\\arraystretch}{2.4}

\\begin{document}

\\thispagestyle{empty}
\\begin{table}[ht]
\\begin{tabularx}{\\textwidth}{X|X|X|X|X|X|X|X|X|X|X|X|X}
    \\hline
    \\diagbox[innerwidth=3.64em]{PT}{DCB}
'''

footer = '''\\end{tabularx}
\\end{table}

\\end{document}'''

table_line_end = '\\\\ \\hline\n'


def collect_terms(d, kw):
    return {k: d[k] for k in d.keys() if kw in k}


class SelectorMS(Selector):
    @staticmethod
    def loop(dataset, rules, configurator):
        # Always chained.
        for connector in dataset.keys():
            for rule in rules:
                dataset[connector] = rules.filter(dataset[connector])

        return dataset


###########################
# Rules for outer JP loop #
###########################


###########################
# Rules for inner JD loop #
###########################


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
    jd_dict = collect_terms(strategy_dict, 'JD')
    tex_file.write('    ')

    for jd in jd_dict.keys():
        tex_file.write('& ')
        tex_file.write(jd[2:])
        if jd_dict[jd]['depopulation']:
            tex_file.write('$^{depop}$')
        tex_file.write(' ')

    tex_file.write(table_line_end)

    # Generate the rest rows
    jp_dict = collect_terms(strategy_dict, 'JP')

    for jp in jp_dict.keys():
    # for jp in ['JP2', 'JP3', 'JP0', 'JP1', 'JP6', 'JP7', 'JP4', 'JP5', 'JP10',
               # 'JP11', 'JP8', 'JP9']:
        jp_descr = jp_dict[jp]
        tex_file.write('    ')

        # Write the row title first
        tex_file.write(jp[2:])
        tex_file.write('$^{{{}'.format(jp_descr['type']))
        if jp_descr['typeDepop'] != jp_descr['type']:
            tex_file.write('/{}}}$'.format(jp_descr['typeDepop']))
        else:
            tex_file.write('}$')

        # Now loop through all DCB connectors
        num_of_jd_connectors = len(jd_dict)
        for jd in jd_dict.keys():
            tex_file.write(' & ')

            try:
                gbtxs_common = jp_descr['commonConn'][jd]
            except Exception:
                gbtxs_common = []
            try:
                gbtxs_special = jp_descr['specialConn'][jd]
            except Exception:
                gbtxs_special = []
            try:
                gbtxs_depop = jp_descr['depopConn'][jd]
            except Exception:
                gbtxs_depop = []

            # Common connectors are black
            if gbtxs_common:
                for gbtx in gbtxs_common:
                    # Check if there's depopulation within these pins
                    if gbtx in gbtxs_depop:
                        tex_file.write('\\ul{{{}}}'.format(gbtx))
                    else:
                        tex_file.write(str(gbtx))

            # Special connectors are red
            if gbtxs_special:
                for gbtx in gbtxs_special:
                    # Check if there's depopulation within these pins
                    if gbtx in gbtxs_depop:
                        tex_file.write('\\textcolor{{red}}{{\\ul{{{}}}}}'.format(gbtx))
                    else:
                        tex_file.write('\\textcolor{{red}}{{{}}}'.format(gbtx))

        tex_file.write(table_line_end)

    tex_file.write(footer)
