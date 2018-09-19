#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Sep 19, 2018 at 02:51 PM -0400

from pathlib import Path

from pyUTM.io import PcadReaderCached
from pyUTM.selection import SelectorNet, RuleNet
from pyUTM.datatype import GenericNetNode
from AltiumNetlistGen import input_dir, pt_result, dcb_result

netlist = input_dir / Path("backplane_netlists") / Path('Aug21_2018.net')
cache_dir = 'cache'


####################################
# Read info from backplane netlist #
####################################

NetReader = PcadReaderCached(cache_dir, netlist)
netlist_dict = NetReader.read()
netlist_list = list(netlist_dict.keys())


########################################
# Cross-checking rules for DCB/PigTail #
########################################

class RuleNet_DCB_DCB(RuleNet):
    def match(self, node):
        if isinstance(node, GenericNetNode):
            return True
        else:
            return False


class RuleNet_DCB_PT_NetName_Inconsistent(RuleNet):
    def match(self, node):
        if node.PT is not None and node.DCB is not None \
                and self.reference[node]['NETNAME'] != \
                self.netlist_dict[node]['NETNAME']:
            return True
        else:
            return False

    def process(self, node):
        return (
            'DCB-PT',
            "NETNAME inconsistent: Tom's: {}, Zishuo: {}, NODE: {}".format(
                self.netlist_dict[node]['NETNAME'],
                self.reference[node]['NETNAME'],
                self.node_to_str(node)
            )
        )


class RuleNet_Node_NotIn(RuleNet):
    def match(self, node):
        if node not in self.netlist_list:
            return True
        else:
            return False

    def process(self, node):
        return (
            'Not Implemented by Tom',
            "NOT present in Tom's net: NET: {}, NODE: {}".format(
                self.reference[node]['NETNAME'], self.node_to_str(node)
            )
        )


class RuleNet_ForRefOnly(RuleNet):
    def match(self, node):
        if self.reference[node]['NETNAME'] is None:
            return True
        else:
            return False

    def process(self, node):
        return (
            'For Reference Only',
            "NOT populated: ATTR: {}, NODE: {}".format(
                self.reference[node]['ATTR'], self.node_to_str(node)
            )
        )


net_rules = [
    RuleNet_ForRefOnly(netlist_dict, netlist_list, pt_result),
    RuleNet_Node_NotIn(netlist_dict, netlist_list, pt_result),
    RuleNet_DCB_PT_NetName_Inconsistent(netlist_dict, netlist_list, pt_result),
    # RuleNet_DCB_PT_In(netlist_dict, netlist_list, pt_result),
    # RuleNet_DCB_PT_NotIn(netlist_dict, netlist_list, pt_result),
    # RuleNet_Node_NotIn(net_descr, pt_result),
    # RuleNet_Node_In_NetNameAgree(net_descr, pt_result),
    # RuleNet_Node_In_NetNameNotAgree(net_descr, pt_result)
]


################################################
# Compare Tom's connections with Zishuo's spec #
################################################

NetSelector = SelectorNet(pt_result, net_rules)
print('')
print('====ERRORS for Backplane connections====')
net_result = NetSelector.do()

for section in net_result.keys():
    print('========{}========'.format(section))
    for entry in net_result[section]:
        print(entry)
    print('')
