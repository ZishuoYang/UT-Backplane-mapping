#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Sep 18, 2018 at 05:38 PM -0400

from pathlib import Path

from pyUTM.io import PcadReader
from pyUTM.selection import SelectorNet, RuleNet
from pyUTM.datatype import GenericNetNode
from AltiumNetlistGen import input_dir, pt_result

netlist = input_dir / Path("backplane_netlists") / Path('Aug21_2018.net')


####################################
# Read info from backplane netlist #
####################################

NetReader = PcadReader(netlist)
net_descr = NetReader.read()


########################################
# Cross-checking rules for DCB/PigTail #
########################################

class RuleNet_DCB_DCB(RuleNet):
    def match(self, node):
        if isinstance(node, GenericNetNode):
            return True
        else:
            return False


class RuleNet_DCB_PT_In(RuleNet):
    def match(self, node):
        if node.PT is not None and node.DCB is not None and \
                node in self.netlist_node_dict_keys_list:
            return True
        else:
            return False


class RuleNet_DCB_PT_NotIn(RuleNet):
    def match(self, node):
        if node.PT is not None and node.DCB is not None:
            return True
        else:
            return False

    def process(self, node):
        return (
            'DCB-PT',
            "NOT present in Tom's net: NET: {}, NODE: {}".format(
                self.reference[node]['NETNAME'], self.node_to_str(node)
            )
        )


class RuleNet_Node_NotIn(RuleNet):
    def match(self, node):
        if node not in self.netlist_node_dict_keys_list:
            return True
        else:
            return False

    def process(self, node):
        return (
            'DCB-None or PT-None',
            "NOT present in Tom's net: NET: {}, NODE: {}".format(
                self.reference[node]['NETNAME'], self.node_to_str(node)
            )
        )


class RuleNet_Node_In_NetNameAgree(RuleNet):
    def match(self, node):
        if self.reference[node]['NETNAME'] == \
                self.netlist_node_dict[node]['NETNAME']:
            return True
        else:
            return False


class RuleNet_Node_In_NetNameNotAgree(RuleNet):
    def match(self, node):
        return True

    def process(self, node):
        return (
            'DCB-None or PT-None',
            "NETNAME DOES NOT agree: Tom: {}, Zishuo: {}, NODE: {}".format(
                self.netlist_node_dict[node]['NETNAME'],
                self.reference[node]['NETNAME'], self.node_to_str(node)
            )
        )


net_rules = [
    RuleNet_DCB_PT_In(net_descr, pt_result),
    RuleNet_DCB_PT_NotIn(net_descr, pt_result),
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
