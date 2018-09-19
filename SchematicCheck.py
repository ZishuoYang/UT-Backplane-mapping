#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri Aug 31, 2018 at 04:53 PM -0400

from pathlib import Path

from pyUTM.io import PcadReader
from AltiumNetlistGen import input_dir, pt_result

netlist = input_dir / Path("backplane_netlists") / Path('Aug21_2018.net')


####################################
# Read info from backplane netlist #
####################################

NetReader = PcadReader(netlist)
all_nets_dict = NetReader.readnets()
net_descr = NetReader.read(all_nets_dict)
net_result = list(net_descr.keys())


################################################
# Compare Tom's connections with Zishuo's spec #
################################################

def nbdir(obj):
    candidate = [attr for attr in dir(obj) if not attr.startswith('_')]
    return [attr for attr in candidate if attr not in ['count', 'index']]


def node_to_str(node):
    attrs = nbdir(node)

    s = ''
    for a in attrs:
        s += (a + ': ')
        if getattr(node, a) is not None:
            s += getattr(node, a)
        else:
            s += 'None'
        s += ', '

    return s[:-2]


print('')
print('====ERRORS for Backplane connections====')

for node in pt_result.keys():
    if node.PT is not None and node.DCB is not None:
        if node in net_result:
            pass
        else:
            print("node in NET {} not present in Tom's net: {}".format(
                pt_result[node]['NETNAME'], node_to_str(node)
            ))

    elif pt_result[node]['NETNAME'] is not None:
        if node in net_result:
            # Also check if the net list name is consistent
            if pt_result[node]['NETNAME'] in net_descr[node]['NETNAME']:
                pass
            else:
                print("netlist name inconsistent: Zishuo: {}; Tom: {}; node: {}".format(
                    pt_result[node]['NETNAME'], net_descr[node]['NETNAME'],
                    node_to_str(node)
                ))
        else:
            print("non PT-DCB node in NET {} not present in Tom's net: {}".format(
                pt_result[node]['NETNAME'], node_to_str(node)
            ))
