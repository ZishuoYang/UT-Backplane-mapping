#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Mar 06, 2019 at 11:57 PM -0500

import re

from datetime import datetime
from pathlib import Path
from os.path import basename

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.io import PcadNaiveReader, PcadReader
from pyUTM.io import netnode_to_netlist
from pyUTM.io import write_to_file
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

def find_backplane_type(filename):
    if 'true' in filename:
        return 'true'
    elif 'mirror' in filename:
        return 'mirror'
    else:
        return 'unknown'


def generate_log_filename(time_format="%Y-%m-%d_%H%M%S", file_extension='.log'):
    header, _ = basename(__file__).split('.', 1)
    filename = sys.argv[1].lower()
    type = find_backplane_type(filename)
    time = datetime.now().strftime(time_format)
    return log_dir / Path(header+'-'+type+'-'+time+file_extension)


def write_to_log(filename, data, **kwargs):
    output = []

    for section in sorted(data.keys()):
        output.append('========{}========'.format(section))
        for entry in data[section]:
            output.append(entry)
        output.append('')

    write_to_file(filename, output, **kwargs)


####################################
# Read info from backplane netlist #
####################################

NetReader = PcadNaiveReader(netlist)
netlist_dict = NetReader.read()

# FIXME: Because CERN people didn't use the correct connector, we are manually
# swapping connector pins for now. This should be removed once the CERN people
# start to use the corrected libraries.
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


##############################
# Rules to check raw netlist #
##############################

class RuleNetlist_DepopDiffElksGamma(RuleNetlist):
    def match(self, netname, components):
        if netname in self.ref_netlist and \
                self.OR([
                    bool(re.search(r'^JP8|^JP9|^JP10|^JP11', x[0]))
                    for x in components
                ]):
            return True
        else:
            return False

    def process(self, netname, components):
        if self.comp_match(components):
            return (
                '1. Depopulated differential pairs biasing resistor',
                'No depopulation component found in {}'.format(netname)
            )
        else:
            return self.NETLISTCHECK_PROCESSED_NO_ERROR_FOUND

    def comp_match(self, components):
        return not self.OR([
            bool(re.search(r'^RB_\d+|^RBSP\d+|^CXRB_\d+', x[0]))
            for x in components
        ])


class RuleNetlist_DepopDiffElksBeta(RuleNetlist_DepopDiffElksGamma):
    def match(self, netname, components):
        if netname in self.ref_netlist:
            return True
        else:
            return False

    def comp_match(self, components):
        return not self.OR([
            bool(re.search(r'^RB_\d+|^CXRB_\d+', x[0]))
            for x in components
        ])


class RuleNetlist_NeverUsedFROElks(RuleNetlist):
    def __init__(self):
        pass

    def match(self, netname, components):
        if '_FRO_' in netname and '_ELK_' in netname:
            return True
        else:
            return False

    def process(self, netname, components):
        if not self.OR([
                bool(re.search(r'^R\d+', x[0])) for x in components
        ]):
            return (
                '2. Never used elinks',
                'No biasing resistor found in {}'.format(netname)
            )
        else:
            return RuleNetlist.NETLISTCHECK_PROCESSED_NO_ERROR_FOUND


################################
# Do checks on the raw netlist #
################################

all_diff_nets = []
for jp in pt_result_true_depop_aux.keys():
    for node in pt_result_true_depop_aux[jp]['Depopulation: ELK']:
        all_diff_nets.append(
            pt_result_true_depop_aux[jp]['Depopulation: ELK'][node]['NETNAME']
        )

raw_net_rules = [
    RuleNetlist_DepopDiffElksGamma(all_diff_nets),
    RuleNetlist_DepopDiffElksBeta(all_diff_nets),
    RuleNetlist_NeverUsedFROElks()
]

RawNetChecker = SelectorNet(netlist_dict, raw_net_rules)
result_check_raw_net = RawNetChecker.do()


#####################################
# Do net hopping on the raw netlist #
#####################################

NetHopper = CurrentFlow([r'^R\d+', r'^C\d+', r'^NT\d+', r'^CXRB_\d+',
                         r'^RB_\d+|^RBSP\d+'])
PcadReader.make_equivalent_nets_identical(
    netlist_dict, NetHopper.do(netlist_dict)
)


#################################
# Rules to check hopped netlist #
#################################

class RuleNetlistHopped_SingleToDiffN(RuleNetlist):
    def match(self, netname, components):
        return bool(re.match(
            r'JD\d_JP\d_EC_(RESET_GPIO|HYB_i2C_SDA|HYB_i2C_SCL)_\d_N$',
            netname
        ))

    def process(self, netname, components):
        result = RuleNetlist.NETLISTCHECK_PROCESSED_NO_ERROR_FOUND

        for c in components:
            if c not in self.ref_netlist['GND']:
                result = (
                    '4. Not connected to GND',
                    'The following net is not connected to GND: {}'.format(
                        netname)
                )
                break

        return result


class RuleNetlistHopped_NonExistComp(RuleNetlist):
    def match(self, netname, components):
        if netname in self.ref_netlist.keys():
            return True

        else:
            return False

    def process(self, netname, components):
        missing_components = []

        for ref_comp in self.ref_netlist[netname]:
            if ref_comp[1] is None:  # Only the connector is specified,
                if ref_comp[0] not in map(lambda x: x[0], components):
                    missing_components.append(ref_comp[0])

            elif ref_comp not in components:
                missing_components.append('-'.join(ref_comp))

        if len(missing_components) > 0:
            missing_components_str = ', '.join(missing_components)
            return (
                '3. Components missing',
                'The following components are missing in the expected net {}: {}'.format(
                    netname, missing_components_str)
            )
        else:
            return RuleNetlist.NETLISTCHECK_PROCESSED_NO_ERROR_FOUND


###################################
# Do checks on the hopped netlist #
###################################

hopped_net_rules = [
    RuleNetlistHopped_SingleToDiffN(netlist_dict),
    RuleNetlistHopped_NonExistComp(backplane_netlist_result_true)
]

HoppedNetChecker = SelectorNet(netlist_dict, hopped_net_rules)
result_check_hopped_net = HoppedNetChecker.do()


################################
# Rules for copy-paste netlist #
################################

class RuleNetlistCopyPaste_NonExistNet(RuleNetlist):
    def __init__(self, ref_netlist, ignore):
        self.ignore = ignore
        super().__init__(ref_netlist)

    def match(self, netname, components):
        if netname not in self.ref_netlist.keys():
            return True
        else:
            return False

    def process(self, netname, components):
        if True in [bool(re.match(x, netname)) for x in self.ignore]:
            return (
                '6. Specified nets not exist but ignored',
                'The following net is missing in the implementation, but ignored: {}'.format(
                    netname)
            )
        else:
            return (
                '5. Specified nets not exist',
                'The following net is missing in the implementation: {}'.format(
                    netname)
            )


#######################################
# Do checks on the copy-paste netlist #
#######################################

copy_paste_net_rules = [
    RuleNetlistCopyPaste_NonExistNet(
        netlist_dict,
        [r'JD\d+_FRO_B[13]',
         r'JD\d+_FRO_(MC|EC)_SEC_DOUT_ELK_[NP]',
         r'JD\d+_FRO_DC_OUT_RCLK\d_[NP]',
         r'JD\d+_FRO_MC_SEC_CLK_ELK_[NP]'
         ])
]

CopyPasteNetChecker = SelectorNet(backplane_netlist_result_true,
                                  copy_paste_net_rules)
result_check_copy_paste_net = CopyPasteNetChecker.do()


##########
# Output #
##########

output_result = {**result_check_raw_net, **result_check_hopped_net,
                 **result_check_copy_paste_net}

try:
    log_filename = sys.argv[2]
except IndexError:
    log_filename = generate_log_filename()

write_to_log(log_filename, output_result)
