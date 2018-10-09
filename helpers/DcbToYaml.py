#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Oct 09, 2018 at 12:58 PM -0400

import yaml

from pathlib import Path
from collections import OrderedDict

import sys
sys.path.insert(0, '..')

from pyUTM.datatype import ExcelCell
from pyUTM.io import XLReader
from pyUTM.io import unflatten
from pyUTM.legacy import PADDING, DEPADDING
from pyUTM.legacy import PINID, CONID
from pyUTM.legacy import make_entries

input_dir = Path('..') / Path('input')

dcb_filename = input_dir / Path(
    'backplaneMapping_SEAMPins_trueType_v5.2.xlsm')
dcb_yaml_filename = input_dir / Path('backplane_mapping_DCB_true.yml')


###########
# Helpers #
###########

def str_presenter(dumper, data):
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
yaml.add_representer(ExcelCell, str_presenter)

# Configure yaml so that OrderedDict is dumped as regular dict
yaml.add_representer(
    OrderedDict,
    lambda self, data:  self.represent_mapping(
        'tag:yaml.org,2002:map', data.items()
    )
)


#######################
# Read from DCB Excel #
#######################

DcbReader = XLReader(dcb_filename)
dcb_descr = DcbReader.read(range(0, 12), 'B5:K405',
                           sortby=lambda d: PADDING(d['SEAM pin']))


####################
# Reformat entries #
####################

dcb_yaml_dict = OrderedDict()
for idx in range(0, len(dcb_descr)):
    connector = 'JD' + str(idx)
    tmp_entries = []

    for entry in dcb_descr[idx]:
        # Make sure there's no padding for the pins.
        entry['SEAM pin'] = DEPADDING(entry['SEAM pin'])
        entry['SEAM pin D'] = PINID(entry['SEAM pin D'])

        # Make sure 'ref' is stored as a number
        entry['ref'] = int(entry['ref'])

        entries = make_entries(
            tmp_entries, entry,
            'Pigtail pin', 'Pigtail slot',
            PINID(entry['Pigtail pin']),
            CONID(entry['Pigtail slot'], lambda x: 'JP'+str(int(x)))
        )

    # Now unflatten the list
    dcb_yaml_dict[connector] = unflatten(tmp_entries, 'SEAM pin')


#################
# Generate yaml #
#################

with open(dcb_yaml_filename, 'w') as yaml_file:
    yaml.dump(dcb_yaml_dict, yaml_file, default_flow_style=False)
