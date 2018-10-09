#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Oct 09, 2018 at 12:36 PM -0400

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

input_dir = Path('..') / Path('input')
pt_yaml_filename = input_dir / Path('backplane_mapping_PT_true.yml')

output_dir = Path('..') / Path('output')
output_dot_filename = output_dir / Path('pt_dcb_connection_optimizer.dot')


#####################
# Read from PT yaml #
#####################

with open(pt_yaml_filename) as yaml_file:
    pt_dict = yaml.safe_load(yaml_file)


########################################
# Find connectivity between PT and DCB #
########################################
# NOTE: DCB-DCB connections are ignored.
