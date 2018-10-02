#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Oct 02, 2018 at 04:45 PM -0400

import yaml

from pathlib import Path
from collections import defaultdict
from yaml.representer import Representer

import sys
sys.path.insert(0, '..')

from pyUTM.io import XLReader
from pyUTM.selection import RulePD

input_dir = Path('..') / Path('input')

brkoutbrd_filename = input_dir / Path(
    'BrkOutBrd_Pin_Assignments_20180917.xlsx')
brkoutbrd_yaml_filename = input_dir / Path('brkoutbrd_pin_assignments.yml')

pt_filename = input_dir / Path(
    'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.2.xlsm')
pt_yaml_filename = input_dir / Path('backplane_mapping_PT_true.yml')

# Configure yaml so that defaultdict is dumped as regular dict
yaml.add_representer(defaultdict, Representer.represent_dict)


###########
# Generic #
###########

def xstr(s):
    if s is None:
        return None
    return str(s)


#########################################
# Breakout board pin assignment to yaml #
#########################################

def sep_connector_pin(s):
    connector, pin = s.split('-', 1)
    return (connector, pin)


BrkReader = XLReader(brkoutbrd_filename)
cell_range_read_spec = {
    'A4:B18':  {'A': 'Signal ID', 'B': 'Connector & Pin'},
    'C4:D18':  {'D': 'Signal ID', 'C': 'Connector & Pin'},
    'A55:B69':  {'A': 'Signal ID', 'B': 'Connector & Pin'},
    'C55:D69':  {'D': 'Signal ID', 'C': 'Connector & Pin'},
    'F4:G18':  {'F': 'Signal ID', 'G': 'Connector & Pin'},
    'H4:I18':  {'I': 'Signal ID', 'H': 'Connector & Pin'},
    'F55:G69':  {'F': 'Signal ID', 'G': 'Connector & Pin'},
    'H55:I69':  {'I': 'Signal ID', 'H': 'Connector & Pin'},
    'A106:B120':  {'A': 'Signal ID', 'B': 'Connector & Pin'},
    'C106:D120':  {'D': 'Signal ID', 'C': 'Connector & Pin'},
    'F106:G120':  {'F': 'Signal ID', 'G': 'Connector & Pin'},
    'H106:I120':  {'I': 'Signal ID', 'H': 'Connector & Pin'},
    'K4:L53':  {'K': 'Signal ID', 'L': 'Connector & Pin'},
    'M4:N53':  {'N': 'Signal ID', 'M': 'Connector & Pin'},
    'K55:L104':  {'K': 'Signal ID', 'L': 'Connector & Pin'},
    'M55:N104':  {'N': 'Signal ID', 'M': 'Connector & Pin'},
    'K106:L155':  {'K': 'Signal ID', 'L': 'Connector & Pin'},
    'M106:N155':  {'N': 'Signal ID', 'M': 'Connector & Pin'},
}

brkoutbrd_pin_assignments = []
for cell_range in cell_range_read_spec.keys():
    brkoutbrd_pin_assignments.extend(
        BrkReader.read(['PinAssignments'], cell_range,
                       headers=cell_range_read_spec[cell_range])[0]
    )

brkoutbrd_yaml_dict = defaultdict(list)
for entry in brkoutbrd_pin_assignments:
    connector, pin = sep_connector_pin(entry['Connector & Pin'])
    brkoutbrd_yaml_dict[connector].append({pin: {
        'Signal ID': xstr(entry['Signal ID'])}
    })

# Sort entries based on pins
for connector in brkoutbrd_yaml_dict:
    brkoutbrd_yaml_dict[connector].sort(key=lambda x: int(list(x.keys())[0]))

with open(brkoutbrd_yaml_filename, 'w') as yaml_file:
    yaml.dump(brkoutbrd_yaml_dict, yaml_file, default_flow_style=False)


##############
# PT to yaml #
##############

PtReader = XLReader(pt_filename)
pt_descr = PtReader.read(range(0, 12), 'B5:K405',
                         sortby=lambda d: RulePD.PADDING(d['Pigtail pin']))
