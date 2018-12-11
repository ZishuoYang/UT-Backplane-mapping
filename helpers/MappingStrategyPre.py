#!/usr/bin/env python
#
# License: MIT
# Last Change: Mon Dec 10, 2018 at 11:11 PM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

from pyUTM.selection import Rule, Selector
from pyUTM.common import collect_terms

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

strategy_yaml_filename = input_dir / Path('mapping_strategy.yml')
strategy_tex_true_filename  = output_dir / Path('mapping_strategy-true.tex')


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
        return spec


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


class SelectorJP(Selector):
    def __init__(self, *args,
                 loop_order=lambda x:
                 filter(lambda y: y.startswith('JP'), x.keys())):
        super().__init__(*args)
        self.loop_order = loop_order

    def do(self):
        dataset = self.dataset
        processed_dataset = {}

        for connector in self.loop_order(dataset):
            # Apply rules in this selector, not chained
            for rule in self.rules:
                processed_dataset[connector] = rule.filter(
                    connector, dataset[connector], dataset)
            # Put the processed data to the nested selector.
            processed_dataset[connector] = self.nested.do(
                processed_dataset[connector])

        return processed_dataset


###########################
# Rules for inner JD loop #
###########################

class RuleJD_FindConnection(RuleMapping):
    def filter(self, connector, dataset):
        dataset[connector] = ''

        if connector in dataset['base']:
            for gbtx in dataset['base'][connector]:
                gbtx_str = self.normal_gbtx(gbtx)

                if 'subConn' in dataset.keys() and \
                        connector in dataset['subConn'] and \
                        gbtx in dataset['subConn'][connector]:
                    gbtx_str = self.sub_gbtx(gbtx_str)

                dataset[connector] += gbtx_str

        return dataset

    @staticmethod
    def normal_gbtx(idx):
        return str(idx)

    @staticmethod
    def sub_gbtx(idx):
        return '\\st{{{}}}'.format(idx)

    @staticmethod
    def depop_gbtx(idx, ref):
        if idx in ref:
            return '\\ul{{{}}}'.format(idx)
        else:
            return str(idx)

    @staticmethod
    def addon_gbtx(idx):
        return '\\textcolor{{red}}{{{}}}'.format(idx)


class RuleJD_Format(RuleMapping):
    pass


class SelectorJD(SelectorJP):
    def __init__(self, *args, loop_order=lambda x:
                 ['JD'+str(i) for i in range(0, 12)]):
        super().__init__(*args, loop_order=loop_order)

    def do(self, dataset):
        for connector in self.loop_order(dataset):
            for rule in self.rules:
                dataset = rule.filter(connector, dataset)

        return dataset


###################################
# Read from mapping strategy yaml #
###################################

with open(strategy_yaml_filename) as yaml_file:
    strategy_dict = yaml.safe_load(yaml_file)


##############################
# Generate tex for true-type #
##############################

selectorInner = SelectorJD(strategy_dict,
                           [RuleJD_FindConnection()]
                           # [RuleMappingTester()]
                           )

selectorMap = SelectorJP(strategy_dict,
                         [RuleJP_Header(), RuleJP_BaseInit()],
                         selectorInner
                         )

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
                    # else:
                        # tex_file.write(str(gbtx))

            # # Special connectors are red
            # if gbtxs_special:
                # for gbtx in gbtxs_special:
                    # # Check if there's depopulation within these pins
                    # if gbtx in gbtxs_depop:
                        # tex_file.write('\\textcolor{{red}}{{\\ul{{{}}}}}'.format(gbtx))
                    # else:

        # tex_file.write(table_line_end)

    # tex_file.write(footer)
