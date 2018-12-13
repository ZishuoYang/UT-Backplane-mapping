#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 13, 2018 at 10:57 AM -0500

import yaml

from pathlib import Path
from collections import OrderedDict

import sys
sys.path.insert(0, '..')

from pyUTM.datatype import ExcelCell
from pyUTM.io import XLReader
from pyUTM.legacy import PADDING, DEPADDING
from pyUTM.legacy import PINID, CONID
from pyUTM.legacy import make_entries
from pyUTM.common import unflatten

input_dir = Path('..') / Path('input')

pt_filename = sys.argv[1]
pt_yaml_filename = input_dir / Path('backplane_mapping_PT.yml')


###########
# Helpers #
###########

def str_representer(dumper, data):
    # check for multiline strings
    if len(data.splitlines()) == 1 and data[-1] == '\n':
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str', data, style='>')
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar(
        'tag:yaml.org,2002:str', data.strip())


# Configure yaml so that ExcelCell is dumped as regular string
yaml.add_representer(ExcelCell, str_representer)

# Configure yaml so that OrderedDict is dumped as regular dict
yaml.add_representer(
    OrderedDict,
    lambda self, data:  self.represent_mapping(
        'tag:yaml.org,2002:map', data.items()
    )
)


def note_generator(s):
    if s is not None and s.font_color is not None:
        if s.font_color.theme != 0 and s.font_color.theme != 1:
            return 'Alpha only'
        elif s.font_color.tint != 0.0:
            return 'Unused'


######################
# Read from PT Excel #
######################

PtReader = XLReader(pt_filename)
pt_descr = PtReader.read(range(0, 12), 'C5:H405',
                         sortby=lambda d: PADDING(d['Pigtail pin']))


####################
# Reformat entries #
####################

pt_yaml_dict = OrderedDict()
for idx in range(0, len(pt_descr)):
    connector = 'JP' + str(idx)
    tmp_entries = []

    for entry in pt_descr[idx]:
        # Make sure there's no padding for the pins.
        entry['Pigtail pin'] = DEPADDING(entry['Pigtail pin'])

        # See if the pin is unused, or alpha only, based on color
        entry['Note'] = note_generator(entry['Signal ID'])

        entries = make_entries(
            tmp_entries, entry,
            'SEAM pin', 'DCB slot',
            PINID(entry['SEAM pin']),
            CONID(entry['DCB slot'], lambda x: 'JD'+str(int(x)))
        )

    # Now unflatten the list
    pt_yaml_dict[connector] = unflatten(tmp_entries, 'Pigtail pin')


#################
# Generate yaml #
#################

with open(pt_yaml_filename, 'w') as yaml_file:
    yaml.dump(pt_yaml_dict, yaml_file, default_flow_style=False)
