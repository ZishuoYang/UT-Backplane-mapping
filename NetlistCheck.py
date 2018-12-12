#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Dec 12, 2018 at 01:04 AM -0500

from pathlib import Path
from os import environ

from pyUTM.io import PcadReader, PcadReaderCached
from pyUTM.selection import SelectorNet, RuleNet
from pyUTM.datatype import GenericNetNode
from AltiumNetlistGen import input_dir, pt_result

netlist = input_dir / Path("backplane_netlists") / Path('PathFinder.net')
cache_dir = 'cache'


####################################
# Read info from backplane netlist #
####################################

if 'IN_TRAVIS_CI' in environ:
    print('Travis CI builder detected. Skip caching.')
    NetReader = PcadReader(netlist)
else:
    NetReader = PcadReaderCached(cache_dir, netlist)

node_dict = NetReader.read()
node_list = list(node_dict.keys())
netlist_dict = NetReader.readnets()


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
                self.node_dict[node]['NETNAME']:
            return True
        else:
            return False

    def process(self, node):
        return (
            'DCB-PT',
            "NETNAME inconsistent: Tom's: {}, Zishuo's: {}, NODE: {}".format(
                self.node_dict[node]['NETNAME'],
                self.reference[node]['NETNAME'],
                self.node_to_str(node)
            )
        )


class RuleNet_DCB_Or_PT_NetName_Inconsistent(RuleNet):
    def match(self, node):
        if self.reference[node]['NETNAME'] != self.node_dict[node]['NETNAME']:
            return True
        else:
            return False

    def process(self, node):
        return (
            'DCB-None or None-PT',
            "NETNAME inconsistent: Tom's: {}, Zishuo's: {}, NODE: {}".format(
                self.node_dict[node]['NETNAME'],
                self.reference[node]['NETNAME'],
                self.node_to_str(node)
            )
        )


class RuleNet_DCB_Or_PT_NetName_Equal_Cavalier(RuleNet):
    def match(self, node):
        if self.reference[node]['NETNAME'] == \
                self.node_dict[node]['NETNAME'].replace('EAST_LV', 'WEST_LV'):
                # ^Seems that 'WEST_LV' and 'EAST_LV' are always equivalent
            return True
        else:
            return False


class RuleNet_Node_NotIn(RuleNet):
    def match(self, node):
        if node not in self.node_list:
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


class RuleNet_One_To_N(RuleNet):
    def __init__(self, netlist_dict, *args):
        self.netlist_dict = netlist_dict
        super().__init__(*args)

    def match(self, node):
        netname_by_tom = self.node_dict[node]['NETNAME']
        netname_by_zishuo = self.reference[node]['NETNAME']

        if netname_by_tom.count('_') >= 2 \
                and netname_by_zishuo.count('_') >= 2:
            node1, node2, signal_id = netname_by_tom.split('_', 2)
            _, _, reference_signal_id = netname_by_zishuo.split('_', 2)

            if signal_id.replace('EAST_LV', 'WEST_LV') == reference_signal_id \
                    or signal_id == reference_signal_id \
                    or ('LV_RETURN' in signal_id and 'LV_RETURN' in
                        reference_signal_id):
                all_nodes_list = \
                    list(zip(*self.netlist_dict[netname_by_tom]))[0]
                node2 = self.replace_arabic_number_to_english(node2)

                if node1 in all_nodes_list:
                    for node in all_nodes_list:
                        # NOTE: If a connector includes 'JS_PT', assuming it is
                        # jumped to another correct component.
                        if 'JS_PT' in node:
                            return True

                    for node in all_nodes_list:
                        if node2 in node:
                            return True

        return False

    # This is needed because Tom is cavalier in picking names.
    @staticmethod
    def replace_arabic_number_to_english(node_name):
        number_replacement_rules = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR',
                                    'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']

        splitted = node_name.split('JPU')
        if len(splitted) == 2:
            name, num = splitted
            return name + '_' + number_replacement_rules[int(num)]

        splitted = node_name.split('JPL')
        if len(splitted) == 2:
            name, num = splitted
            return name + '_' + number_replacement_rules[int(num)]

        return node_name


################################################
# Compare Tom's connections with Zishuo's spec #
################################################

net_rules = [
    RuleNet_ForRefOnly(node_dict, node_list, pt_result),
    RuleNet_Node_NotIn(node_dict, node_list, pt_result),
    RuleNet_DCB_PT_NetName_Inconsistent(node_dict, node_list,
                                        pt_result),
    RuleNet_One_To_N(netlist_dict, node_dict, node_list, pt_result),
    RuleNet_DCB_Or_PT_NetName_Equal_Cavalier(node_dict, node_list,
                                             pt_result),
    RuleNet_DCB_Or_PT_NetName_Inconsistent(node_dict, node_list,
                                           pt_result),
]


NetSelector = SelectorNet(pt_result, net_rules)
print('====ERRORS for Backplane connections====')
net_result = NetSelector.do()

for section in net_result.keys():
    print('========{}========'.format(section))
    for entry in net_result[section]:
        print(entry)
    print('')
