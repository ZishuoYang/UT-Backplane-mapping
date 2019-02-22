#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri Feb 22, 2019 at 01:43 PM -0500

import re

from datetime import datetime
from pathlib import Path
from os.path import basename

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.io import PcadNaiveReader, PcadReader
from pyUTM.io import NetNodeGen
from pyUTM.io import netnode_to_netlist
from pyUTM.sim import CurrentFlow
from pyUTM.selection import SelectorNet, RuleNetlist
from AltiumNetlistGen import pt_result_true, dcb_result_true
from AltiumNetlistGen import pt_result_true_depop_aux

log_dir = Path('log')

# Use first argument as netlist filename.
netlist = sys.argv[1]

# Combine Pigtail and DCB rules into a larger set of rules
backplane_result_true = {**pt_result_true, **dcb_result_true}

# Convert NetNode list to a parsed netlist
backplane_netlist_result_true = netnode_to_netlist(backplane_result_true)


###########
# Helpers #
###########

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

NetReader = PcadNaiveReader(netlist)
netlist_dict = NetReader.read()

# FIXME: Because CERN people didn't use the correct connector, we manually
# swapping connector pins for now. This should be removed once the CERN people
# start to use the correct libraries.
print('Warning: Using the temporary fix to handle the pin letter swap.')

for netname, nodes in netlist_dict.items():
    new_nodes = []

    for n in nodes:
        new_n = list(n)

        if n[1].startswith('J'):
            new_n[1] = 'I' + n[1][1:]

        if n[1].startswith('K'):
            new_n[1] = 'J' + n[1][1:]

        new_nodes.append(tuple(new_n))

    netlist_dict[netname] = new_nodes

node_dict = NetNodeGen().do(netlist_dict)
node_list = list(node_dict.keys())


##############################
# Rules to check raw netlist #
##############################

all_diff_nets = []
for jp in pt_result_true_depop_aux.keys():
    for node in pt_result_true_depop_aux[jp]['Depopulation: ELK']:
        all_diff_nets.append(
            pt_result_true_depop_aux[jp]['Depopulation: ELK'][node]['NETNAME']
        )


class RuleNetlist_DepopDiffElks(RuleNetlist):
    def match(self, netname, components):
        matched = False

        if netname in self.ref_netlist:
            # For Gamma (Beta special) variant:
            if True in map(
                    lambda x: bool(re.search(r'^JP8|^JP9|^JP10|^JP11', x[0])),
                    components):
                if True not in map(
                        lambda x: bool(
                            re.search(r'^RB_\d+|^RBSP\d+|^RxCB_\d+', x[0])),
                        components):
                    matched = True

            # For Beta variant:
            else:
                if True not in map(
                        lambda x: bool(
                            re.search(r'^RB_\d+|^RBSP\d+|^RxCB_\d+', x[0])),
                        components):
                    matched = True

        return matched

    def process(self, netname, components):
        return (
            '1. Depopulated differential pairs biasing resistor',
            'No depopulation component found in {}'.format(netname)
        )


class RuleNetlist_NeverUsedFROElks(RuleNetlist):
    def __init__(self):
        pass

    def match(self, netname, components):
        matched = False

        if '_FRO_' in netname and '_ELK_' in netname:
            if True not in map(
                    lambda x: bool(re.search(r'^R\d+', x[0])), components):
                matched = True

        return matched

    def process(self, netname, components):
        return (
            '2. Never used elinks',
            'No biasing resistor found in {}'.format(netname)
        )


################################
# Do checks on the raw netlist #
################################

raw_net_rules = [
    RuleNetlist_DepopDiffElks(all_diff_nets),
    RuleNetlist_NeverUsedFROElks()
]

RawNetChecker = SelectorNet(netlist_dict, raw_net_rules)
result_check_raw_net = RawNetChecker.do()


#####################################
# Do net hopping on the raw netlist #
#####################################

NetHopper = CurrentFlow()
PcadReader.make_equivalent_nets_identical(
    netlist_dict, NetHopper.do(netlist_dict)
)


#################################
# Rules to check hopped netlist #
#################################


class RuleNetlistHopped_NonExistComp(RuleNetlist):
    def match(self, netname, components):
        matched = False
        self.missing_components = []

        if netname in self.ref_netlist.keys():
            for ref_comp in self.ref_netlist[netname]:
                if ref_comp[1] is None:
                    ref_connector = ref_comp[0]
                    if ref_connector not in map(lambda x: x[0], components):
                        matched = True
                        self.missing_components.append(ref_connector)

                elif ref_comp not in components:
                    matched = True
                    self.missing_components.append('-'.join(ref_comp))

        return matched

    def process(self, netname, components):
        missing_components_str = ', '.join(self.missing_components)
        return (
            '3. Components missing',
            'The following components are missing in the expected net {}: {}'.format(
                netname, missing_components_str)
        )


###################################
# Do checks on the hopped netlist #
###################################

hopped_net_rules = [
    RuleNetlistHopped_NonExistComp(backplane_netlist_result_true)
]

HoppedNetChecker = SelectorNet(netlist_dict, hopped_net_rules)
result_check_hopped_net = HoppedNetChecker.do()


##########
# Output #
##########

output_result = {**result_check_raw_net, **result_check_hopped_net}

try:
    log_filename = sys.argv[2]
except IndexError:
    log_filename = generate_log_filename()

write_to_log(log_filename, output_result)
