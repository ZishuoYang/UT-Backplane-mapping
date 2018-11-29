#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Nov 27, 2018 at 03:58 PM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

from pyUTM.selection import Rule, Loop, Selector
from pyUTM.io import collect_terms

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


class RuleMapping(Rule):
    def match(self, *args):
        pass

    def process(self, *args):
        pass


class RuleMappingTester(RuleMapping):
    def filter(self, connector, spec, *args):
        print('connector is: {}'.format(connector))
        print('spec is: {}'.format(spec))


###########################
# Rules for outer JP loop #
###########################

class RuleJP_Header(RuleMapping):
    def filter(self, connector, spec, full_spec):
        spec['header'] = self.header_gen(
            connector, spec['type'], spec['typeDepop'])
        return spec

    @staticmethod
    def header_gen(connector, type1, type2):
        header = connector[2:]
        header += '$^{{{}'.format(type1)
        if type1 != type2:
            header += '/{}}}$'.format(type2)
        else:
            header += '}$'
        return header


class RuleJP_BaseInit(RuleMapping):
    # Non-idempotent. Which means that our selector can only run once.
    def filter(self, connector, spec, full_spec):
        spec['base'] = self.base_concretify(
            connector, spec['base'], full_spec[spec['base']])
        return spec

    @staticmethod
    def base_concretify(connector, base_connector, base_connector_map):
        connector_idx = int(connector[2:])
        base_connector_idx = int(base_connector[6:])
        idx_shift = connector_idx - base_connector_idx

        connector_map = dict()
        for base_connector in base_connector_map.keys():
            # Chop off 'Base'
            connector = base_connector[4:]
            # Account for the index shift
            connector = connector[:2] + str(int(connector[2:])+idx_shift)
            connector_map[connector] = base_connector_map[base_connector]

        return connector_map


class LoopJP(Loop):
    def __init__(self, loop_order=lambda x:
                 filter(lambda y: y.startswith('JP'), x.keys())):
        self.loop_order = loop_order

    def loop(self, dataset, rules):
        for connector in self.loop_order(dataset):
            for rule in rules:
                dataset[connector] = rule.filter(connector,
                                                 dataset[connector],
                                                 dataset)
        return dataset


###########################
# Rules for inner JD loop #
###########################

class LoopJD(LoopJP):
    pass


###################################
# Read from mapping strategy yaml #
###################################

with open(strategy_yaml_filename) as yaml_file:
    strategy_dict = yaml.safe_load(yaml_file)


##############################
# Generate tex for true-type #
##############################

selectorMap = Selector(strategy_dict,
                       [
                           [RuleJP_Header(), RuleJP_BaseInit()],
                           [RuleMappingTester()]
                       ],
                       [
                           LoopJP(), LoopJD()
                       ])

# Generate the rest of the header
jd_dict = collect_terms(strategy_dict, lambda x: filter(lambda y: 'JD' in y, x))
header_true = ''
for jd in jd_dict.keys():
    header_true += '&'
    header_true += jd[2:]
    if jd_dict[jd]['depopulation']:
        header_true += '$^{depop}$'
    header_true += ' '
header_true += table_line_end


# with open(strategy_tex_filename, 'w') as tex_file:
    # tex_file.write(header)

    # # Fill out the remainder of the header
    # jd_dict = collect_terms(strategy_dict, 'JD')
    # tex_file.write('    ')

    # for jd in jd_dict.keys():
        # tex_file.write('& ')
        # tex_file.write(jd[2:])
        # if jd_dict[jd]['depopulation']:
            # tex_file.write('$^{depop}$')
        # tex_file.write(' ')

    # tex_file.write(table_line_end)

    # # Generate the rest rows
    # jp_dict = collect_terms(strategy_dict, 'JP')

    # # for jp in jp_dict.keys():
    # for jp in ['JP2', 'JP3', 'JP0', 'JP1', 'JP6', 'JP7', 'JP4', 'JP5', 'JP10',
               # 'JP11', 'JP8', 'JP9']:
        # jp_descr = jp_dict[jp]
        # tex_file.write('    ')

        # # Write the row title first
        # tex_file.write(jp[2:])
        # tex_file.write('$^{{{}'.format(jp_descr['type']))
        # if jp_descr['typeDepop'] != jp_descr['type']:
            # tex_file.write('/{}}}$'.format(jp_descr['typeDepop']))
        # else:
            # tex_file.write('}$')

        # # Now loop through all DCB connectors
        # num_of_jd_connectors = len(jd_dict)
        # for jd in jd_dict.keys():
            # tex_file.write(' & ')

            # try:
                # gbtxs_common = jp_descr['commonConn'][jd]
            # except Exception:
                # gbtxs_common = []
            # try:
                # gbtxs_special = jp_descr['specialConn'][jd]
            # except Exception:
                # gbtxs_special = []
            # try:
                # gbtxs_depop = jp_descr['depopConn'][jd]
            # except Exception:
                # gbtxs_depop = []

            # # Common connectors are black
            # if gbtxs_common:
                # for gbtx in gbtxs_common:
                    # # Check if there's depopulation within these pins
                    # if gbtx in gbtxs_depop:
                        # tex_file.write('\\ul{{{}}}'.format(gbtx))
                    # else:
                        # tex_file.write(str(gbtx))

            # # Special connectors are red
            # if gbtxs_special:
                # for gbtx in gbtxs_special:
                    # # Check if there's depopulation within these pins
                    # if gbtx in gbtxs_depop:
                        # tex_file.write('\\textcolor{{red}}{{\\ul{{{}}}}}'.format(gbtx))
                    # else:
                        # tex_file.write('\\textcolor{{red}}{{{}}}'.format(gbtx))

        # tex_file.write(table_line_end)

    # tex_file.write(footer)
