#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 20, 2018 at 01:14 AM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '../pyUTM')

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

pt_yaml_filename  = input_dir / Path('backplane_mapping_PT.yml')
dcb_yaml_filename = input_dir / Path('backplane_mapping_DCB.yml')
dot_filename      = output_dir / Path('pt_dcb_connection_optimizer.dot')


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
    dot_file.write('  nodesep=0.5;\n')

    dot_file.write('  subgraph JD_FIXED_LEFT {\n')
    for c in dcb_connectors[2:4]:
        dot_file.write('    {} [width=1, shape=box];\n'.format(c))
    dot_file.write('  }\n\n')

    dot_file.write('  subgraph JD_FIXED_RIGHT {\n')
    for c in dcb_connectors[10:]:
        dot_file.write('    {} [width=1, shape=box];\n'.format(c))
    dot_file.write('  }\n\n')

    dot_file.write('  subgraph JD_REST {\n')
    for c in dcb_connectors[0:2] + dcb_connectors[4:10]:
        dot_file.write('    {} [width=1, shape=box];\n'.format(c))
    dot_file.write('  }\n\n')

    dot_file.write('  subgraph JP {\n')
    for c in pt_connectors:
        dot_file.write('    {} [width=1, shape=box];\n'.format(c))
    dot_file.write('  }\n\n')

    dot_file.write('  {{ rank=same {} }}\n\n'.format(' '.join(dcb_connectors)))

    dot_file.write('  {\n')
    dot_file.write('    rank=same;\n')
    dot_file.write('    {} [style=invis];\n'.format(' -- '.join(pt_connectors)))
    dot_file.write('    rankdir=LR;\n')
    dot_file.write('  }\n\n')

    for conn in connections:
        dot_file.write('  {} -- {};\n'.format(*reversed(conn)))

    dot_file.write('}\n')
