#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri Aug 31, 2018 at 11:59 AM -0400

from pathlib import Path

from pyUTM.io import PcadReader
from AltiumNetlistGen import input_dir, pt_result

netlist = input_dir / Path("backplane_netlists") / Path('Aug21_2018.net')


####################################
# Read info from backplane netlist #
####################################

NetReader = PcadReader(netlist)
net_descr = NetReader.read()
net_result = net_descr.keys()


################################################
# Compare Tom's connections with Zishuo's spec #
################################################

def nbdir(obj):
    candidate = [attr for attr in dir(obj) if not attr.startswith('_')]
    return [attr for attr in candidate if attr not in ['count', 'index']]


def print_net_node(node):
    attrs = nbdir(node)

    s = ''
    for a in attrs:
        s += (a + ': ')
        if getattr(node, a) is not None:
            s += getattr(node, a)
        else:
            s += 'None'
        s += ', '

    print(s[:-2])


print('')
print('====ERRORS for Backplane connections====')

for node in pt_result.keys():
    if node in net_result:
        pass
    else:
        print("The following node is not present in Tom's net:")
        print_net_node(node)
