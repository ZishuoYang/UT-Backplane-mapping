#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Oct 09, 2018 at 01:34 PM -0400

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

input_dir = Path('..') / Path('input')
pt_yaml_filename = input_dir / Path('backplane_mapping_PT_true.yml')
dcb_yaml_filename = input_dir / Path('backplane_mapping_DCB_true.yml')

output_dir = Path('..') / Path('output')
dot_filename = output_dir / Path('pt_dcb_connection_optimizer.dot')


#########################
# Read from PT/DCB yaml #
#########################

with open(pt_yaml_filename) as yaml_file:
    pt_dict = yaml.safe_load(yaml_file)

with open(dcb_yaml_filename) as yaml_file:
    dcb_dict = yaml.safe_load(yaml_file)


########################################
# Find connectivity between PT and DCB #
########################################
# NOTE: DCB-DCB connections are ignored.

pt_connectors = list(pt_dict.keys())
dcb_connectors = list(dcb_dict.keys())

connections = []

for pt in pt_dict.keys():
    for entry in pt_dict[pt]:
        pt_pin, info = list(entry.items())[0]
        dcb = info['DCB slot']
        if dcb is not None:
            conn = (pt, dcb)
            if conn not in connections:
                connections.append(conn)


#####################
# Generate dot file #
#####################

with open(dot_filename, 'w') as dot_file:
    dot_file.write('graph G {\n')
    dot_file.write('  {{rank=same {}}}\n'.format(' '.join(pt_connectors)))
    dot_file.write('  {{rank=same {}}}\n'.format(' '.join(dcb_connectors)))
    for conn in connections:
        dot_file.write('    {} -- {};\n'.format(*conn))
    dot_file.write('}\n')
