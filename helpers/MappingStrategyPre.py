#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 20, 2018 at 01:15 AM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '../pyUTM')

from pyUTM.selection import Rule, Selector
from pyUTM.common import collect_terms

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

strategy_yaml_filename = input_dir / Path('mapping_strategy.yml')
strategy_tex_true_filename  = output_dir / Path('mapping_strategy-true.tex')


###########
# Helpers #
###########

indent = '    '

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

        if self.connector_in_dict(connector, 'base', dataset):
            for gbtx in dataset['base'][connector]:
                gbtx_str = self.depop_gbtx(
                    connector, gbtx, 'depopConn', dataset)

                if self.gbtx_in_dict(connector, gbtx, 'subConn', dataset):
                    gbtx_str = self.color(self.sub_gbtx(gbtx_str), 'gray')

                dataset[connector] += gbtx_str

        if self.connector_in_dict(connector, 'addOnConn', dataset):
            for gbtx in dataset['addOnConn'][connector]:
                gbtx_str = self.color(self.depop_gbtx(
                    connector, gbtx, 'depopConn', dataset))

                dataset[connector] += gbtx_str

        return dataset

    @classmethod
    def depop_gbtx(cls, connector, gbtx, dict_name, dataset):
        if cls.gbtx_in_dict(connector, gbtx, dict_name, dataset):
            return '\\ul{{{}}}'.format(gbtx)
        else:
            return str(gbtx)

    @classmethod
    def gbtx_in_dict(cls, connector, gbtx, dict_name, dataset):
        if cls.connector_in_dict(connector, dict_name, dataset) and \
                gbtx in dataset[dict_name][connector]:
            return True
        else:
            return False

    @staticmethod
    def connector_in_dict(connector, dict_name, dataset):
        if dict_name in dataset.keys() and connector in dataset[dict_name]:
            return True
        else:
            return False

    @staticmethod
    def sub_gbtx(idx):
        return '\\st{{{}}}'.format(idx)

    @staticmethod
    def color(idx, color='red'):
        return '\\textcolor{{{}}}{{{}}}'.format(color, idx)


class RuleJD_Format(RuleMapping):
    def filter(self, connector, dataset):
        dataset['rowContent'] = dataset['header'] + ' & '
        dataset['rowContent'] += ' & '.join(
            [dataset[jd] for jd in dataset.keys() if 'JD' in jd]
        )
        dataset['rowContent'] += table_line_end
        return dataset


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
# Generate tex for True-type #
##############################

selectorInner = SelectorJD(strategy_dict,
                           [RuleJD_FindConnection(), RuleJD_Format()]
                           # [RuleMappingTester()]
                           )

selectorMap = SelectorJP(strategy_dict,
                         [RuleJP_Header(), RuleJP_BaseInit()],
                         selectorInner
                         )

# Generate the rest of the header
jd_dict = collect_terms(strategy_dict, lambda x: filter(lambda y: 'JD' in y, x))
header_true = indent
for jd in jd_dict.keys():
    header_true += '&'
    header_true += jd[2:]
    if jd_dict[jd]['depopulation']:
        header_true += '$^{depop}$'
    header_true += ' '
header_true += table_line_end

# Generate all subsequent rows
rows = selectorMap.do()

with open(strategy_tex_true_filename, 'w') as tex_file:
    tex_file.write(header)
    tex_file.write(header_true)

    for jp in ['JP'+str(i) for i in range(0, 12)]:
        tex_file.write(indent + rows[jp]['rowContent'])

    tex_file.write(footer)
