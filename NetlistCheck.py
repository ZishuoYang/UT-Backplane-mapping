#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Feb 07, 2019 at 04:58 PM -0500

import re

from datetime import datetime
from pathlib import Path
from os.path import basename

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.legacy import PcadBackPlaneReader
from pyUTM.selection import SelectorNet, RuleNet
from pyUTM.datatype import NetNode  # for debugging
from AltiumNetlistGen import pt_result_true, dcb_result_true
from AltiumNetlistGen import pt_result_true_depop_aux

log_dir = Path('log')


###########
# Helpers #
###########

# Use first argument as netlist filename.
netlist = sys.argv[1]

# Combine Pigtail and DCB rules into a larger set of rules
pt_result_true.update(dcb_result_true)


def generate_log_filename(time_format="%Y-%m-%d_%H%M%S", file_extension='.log'):
    header, _ = basename(__file__).split('.', 1)
    filename = sys.argv[1].lower()

    if 'true' in filename:
        type = 'true'
    elif 'mirror' in filename:
        type = 'mirror'
    else:
        type = 'unknown'

    time = datetime.now().strftime(time_format)

    return log_dir / Path(header+'-'+type+'-'+time+file_extension)


def write_to_log(filename, data, mode='w', eol='\n'):
    with open(filename, mode) as f:
        for section in sorted(data.keys()):
            f.write('========{}========'.format(section) + eol)
            for entry in data[section]:
                f.write(entry + eol)
            f.write(eol)


####################################
# Read info from backplane netlist #
####################################

NetLegacyReader = PcadBackPlaneReader(netlist)

node_dict, netlist_dict = NetLegacyReader.read()
node_list = list(node_dict.keys())


##########################################
# Check differential signal depopulation #
##########################################

all_diff_nets = []
for jp in pt_result_true_depop_aux.keys():
    for node in pt_result_true_depop_aux[jp]['Depopulation: ELK']:
        all_diff_nets.append(
            pt_result_true_depop_aux[jp]['Depopulation: ELK'][node]['NETNAME']
        )

print("Checking depopulated differential pairs...")
for diff_net in all_diff_nets:
    components = netlist_dict[diff_net]
    if True not in map(lambda x: bool(re.search(r'^R\d+', x)), components):
        print("No resistor found in {}".format(diff_net))


########################################
# Cross-checking rules for DCB/Pigtail #
########################################

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
            '2. DCB-PT',
            "NETNAME inconsistent: Implemented: {}, Specified: {}, NODE: {}".format(
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
            '3. DCB-None or None-PT',
            "NETNAME inconsistent: Implemented: {}, Specified: {}, NODE: {}".format(
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
            '1. Not Implemented',
            "NOT implemented: NET: {}, NODE: {}".format(
                self.reference[node]['NETNAME'], self.node_to_str(node)
            )
        )


class RuleNet_ForRefOnly(RuleNet):
    def match(self, node):
        if self.reference[node]['ATTR'] == '_FRO_':
            return True
        else:
            return False

    def process(self, node):
        return (
            '4. For Reference Only',
            "NOT populated: NETNAME: {}, NODE: {}".format(
                self.reference[node]['NETNAME'], self.node_to_str(node)
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
    RuleNet_ForRefOnly(node_dict, node_list, pt_result_true),
    RuleNet_Node_NotIn(node_dict, node_list, pt_result_true),
    RuleNet_DCB_PT_NetName_Inconsistent(node_dict, node_list,
                                        pt_result_true),
    RuleNet_One_To_N(netlist_dict, node_dict, node_list, pt_result_true),
    RuleNet_DCB_Or_PT_NetName_Equal_Cavalier(node_dict, node_list,
                                             pt_result_true),
    RuleNet_DCB_Or_PT_NetName_Inconsistent(node_dict, node_list,
                                           pt_result_true),
]

# Debug
for rule in net_rules:
    rule.debug_node = NetNode('JD8', 'A1')

NetSelector = SelectorNet(pt_result_true, net_rules)
net_result = NetSelector.do()

try:
    log_filename = sys.argv[2]
except IndexError:
    log_filename = generate_log_filename()

write_to_log(log_filename, net_result)
