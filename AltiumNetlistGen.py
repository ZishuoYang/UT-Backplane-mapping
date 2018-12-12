#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Dec 12, 2018 at 03:41 AM -0500

from pathlib import Path

from pyUTM.io import write_to_csv
from pyUTM.io import YamlReader
from pyUTM.selection import SelectorPD, RulePD
from pyUTM.datatype import NetNode
from pyUTM.datatype import ExcelCell
from pyUTM.common import flatten, transpose, split_netname
from pyUTM.common import jd_swapping_true

input_dir = Path('input')
output_dir = Path('output')

brkoutbrd_filename = input_dir / Path('brkoutbrd_pin_assignments.yml')
pt_filename = input_dir / Path('backplane_mapping_PT.yml')
dcb_filename = input_dir / Path('backplane_mapping_DCB.yml')

pt_true_result_output_filename = output_dir / Path(
    'AltiumNetlist_PT_Full_TrueType.csv')
dcb_true_result_output_filename = output_dir / Path(
    'AltiumNetlist_DCB_Full_TrueType.csv')

#############################
# Read signals and mappings #
#############################

# Read pin assignments from breakout board #
BrkoutbrdReader = YamlReader(brkoutbrd_filename)
brkoutbrd_descr = BrkoutbrdReader.read()

brkoutbrd_data = map(transpose, brkoutbrd_descr.values())
brkoutbrd_nested_signals = list(map(
    lambda x: [s for s in x['Signal ID'] if s is not None and s != 'GND'],
    brkoutbrd_data
))

# We intent to keep 'Signal ID' only, in a list.
brkoutbrd_pin_assignments = [item for sublist in brkoutbrd_nested_signals
                             for item in sublist]

# Read info from PigTail #
PtReader = YamlReader(pt_filename)
pt_descr = PtReader.read(flattener=lambda x: flatten(x, 'Pigtail pin'))

# Read info from DCB #
DcbReader = YamlReader(dcb_filename)
dcb_descr = DcbReader.read(flattener=lambda x: flatten(x, 'SEAM pin'))


########################################
# Define rules for PigTail Altium list #
########################################

# This needs to be placed at the end of the rules list.  It always returns
# 'True' to handle entries NOT matched by any other rules.
class RulePT_Default(RulePD):
    def match(self, data, pt_idx):
        return True

    def process(self, data, pt_idx):
        net_name = self.PT_PREFIX + str(pt_idx) + '_' + data['Signal ID']
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': '_ForRefOnly_'}
        )


class RulePT_PathFinder(RulePD):
    def match(self, data, pt_idx):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if pt_idx in [0, 1]:
            return False

        # For path finder, skip non-BOB nets when not in slot 0 or 1
        keywords = ['LV_SOURCE', 'LV_RETURN', 'LV_SENSE', 'THERMISTOR']
        result = [False if kw in data['Signal ID'] else True for kw in keywords]
        return self.AND(result)

    def process(self, data, pt_idx):
        # Note: here the matching nodes will have placeholder in netlist file.
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': None, 'ATTR': '_PlaceHolder_'}
        )


class RulePT_DCB(RulePD):
    def match(self, data, pt_idx):
        if data['SEAM pin'] is not None:
            # Which means that this PT pin is connected to a DCB pin.
            return True
        else:
            return False

    def process(self, data, pt_idx):
        net_name = \
            self.DCB_PREFIX + self.DCBID(data['DCB slot']) + '_' + \
            self.PT_PREFIX + str(pt_idx) + '_' + \
            data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + self.DCBID(data['DCB slot']),
                'DCB_PIN': data['SEAM pin'],
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RulePT_NotConnected(RulePD):
    def match(self, data, pt_idx):
        if data['SEAM pin'] is None and \
                self.OR([
                        'ASIC' in data['Signal ID'],
                        '_CLK_' in data['Signal ID'],
                        'TFC' in data['Signal ID'],
                        'THERMISTOR' in data['Signal ID']
                        ]):
            # Which means that this PT pin is not connected to a DCB pin.
            return True
        else:
            return False

    def process(self, data, pt_idx):
        net_name = 'GND'
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RulePT_PTLvSource(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, pt_idx):
        if 'LV_SOURCE' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, pt_idx):
        net_name = \
            self.PT_PREFIX + str(pt_idx) + '_' + data['Signal ID']
        attr = '_ForRefOnly_'

        for rule in self.rules:
            pt_name, tail = rule.split('_', 1)
            if self.PT_PREFIX+str(pt_idx) == pt_name and \
                    data['Signal ID'] in tail:
                net_name = rule
                attr = None
                break
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': attr}
        )


class RulePT_PTLvReturn(RulePT_PTLvSource):
    def match(self, data, pt_idx):
        if 'LV_RETURN' in data['Signal ID']:
            return True
        else:
            return False


class RulePT_PTLvSense(RulePT_PTLvSource):
    def match(self, data, pt_idx):
        if 'LV_SENSE' in data['Signal ID']:
            return True
        else:
            return False


class RulePT_PTThermistor(RulePT_PTLvSource):
    def match(self, data, pt_idx):
        if 'THERMISTOR' in data['Signal ID']:
            return True
        else:
            return False


# Put PTSingleToDiff rule above the general PT-DCB rule
class RulePT_PTSingleToDiffP(RulePD):
    def match(self, data, pt_idx):
        if not data['Signal ID'].endswith('_N') and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, pt_idx):
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = \
                self.DCB_PREFIX + self.DCBID(data['DCB slot']) + '_' + \
                self.PT_PREFIX + str(pt_idx) + '_THERM_' + \
                data['Signal ID'] + '_P'
        else:
            net_name = \
                self.DCB_PREFIX + self.DCBID(data['DCB slot']) + '_' + \
                self.PT_PREFIX + str(pt_idx) + '_' + \
                data['Signal ID'] + '_P'
        return (
            {
                'DCB': self.DCB_PREFIX + self.DCBID(data['DCB slot']),
                'DCB_PIN': data['SEAM pin'],
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RulePT_PTSingleToDiffN(RulePD):
    def match(self, data, pt_idx):
        if data['Signal ID'].endswith('_N') and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, pt_idx):
        dcb_name, tail = data['Signal ID'].split('_', 1)
        net_name = dcb_name + '_' + self.PT_PREFIX + str(pt_idx) + '_' + tail
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RulePT_UnusedToGND(RulePD):
    def match(self, data, pt_idx):
        if data['Note'] == 'Unused':
            return True
        else:
            return False

    def process(self, data, pt_idx):
        return (
            {
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': 'GND', 'ATTR': None}
        )


####################################
# Define rules for DCB Altium list #
####################################

class RuleDCB_Default(RulePD):
    def match(self, data, dcb_idx):
        return True

    def process(self, data, dcb_idx):
        net_name = self.DCB_PREFIX + str(dcb_idx) + '_' + data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': self.DEPADDING(data['SEAM pin'])
            },
            {'NETNAME': net_name, 'ATTR': '_ForRefOnly_'}
        )


class RuleDCB_PathFinder(RulePD):
    def match(self, data, dcb_idx):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if dcb_idx in [0, 2, 4]:
            return False

    def process(self, data, dcb_idx):
        # Note: here the matching nodes will have placeholder in netlist file.
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': self.DEPADDING(data['SEAM pin']),
            },
            {'NETNAME': None, 'ATTR': '_PlaceHolder_'}
        )


class RuleDCB_PT(RulePD):
    def match(self, data, dcb_idx):
        if data['Pigtail pin'] is not None:
            # Which means that this DCB pin is connected to a PT pin.
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + \
            self.PT_PREFIX + self.PTID(data['Pigtail slot']) + '_' + \
            data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': data['SEAM pin'],
                'PT': self.PT_PREFIX + self.PTID(data['Pigtail slot']),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


# Put PTSingleToDiff rule above the general PT-DCB rule
class RuleDCB_PTSingleToDiff(RulePD):
    def match(self, data, dcb_idx):
        if data['Pigtail slot'] is not None and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = \
                self.DCB_PREFIX + str(dcb_idx) + '_' + \
                self.PT_PREFIX + self.PTID(data['Pigtail slot']) + \
                '_THERM_' + data['Signal ID'] + '_P'
        else:
            net_name = \
                self.DCB_PREFIX + str(dcb_idx) + '_' + \
                self.PT_PREFIX + self.PTID(data['Pigtail slot']) + '_' + \
                data['Signal ID'] + '_P'
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': data['SEAM pin'],
                'PT': self.PT_PREFIX + self.PTID(data['Pigtail slot']),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RuleDCB_1V5(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, dcb_idx):
        if data['Signal ID'] == '1.5V':
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + data['Signal ID']

        for rule in self.rules:
            dcb_name, tail = rule.split('_', 1)
            if self.DCB_PREFIX+str(dcb_idx) == dcb_name and \
                    '1V5' in tail and 'SENSE' not in tail:
                net_name = rule
                break
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': self.DEPADDING(data['SEAM pin']),
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RuleDCB_2V5(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, dcb_idx):
        if data['Signal ID'] == '2.5V':
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + data['Signal ID']

        for rule in self.rules:
            if '2V5' in rule and 'SENSE' not in rule:
                dcb1, dcb2, _ = rule.split('_', 2)
                if self.DCB_PREFIX+str(dcb_idx) == dcb1 or \
                        str(dcb_idx) == dcb2:
                    net_name = rule
                    break
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': self.DEPADDING(data['SEAM pin']),
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RuleDCB_1V5Sense(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, dcb_idx):
        if '1V5_SENSE' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + data['Signal ID']

        for rule in self.rules:
            dcb_name, tail = rule.split('_', 1)
            if self.DCB_PREFIX+str(dcb_idx) == dcb_name and \
                    data['Signal ID'][:-2] in tail:
                net_name = rule
                break
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': self.DEPADDING(data['SEAM pin']),
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RuleDCB_GND(RulePD):
    def match(self, data, dcb_idx):
        if 'GND' == data['Signal ID']:
            # Which means that this DCB pin GND (not AGND).
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': data['SEAM pin'],
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RuleDCB_AGND(RuleDCB_GND):
    def match(self, data, dcb_idx):
        if 'AGND' == data['Signal ID']:
            # Which means that this DCB pin AGND (not GND).
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + \
            data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': data['SEAM pin'],
                'PT': data['Pigtail slot'] if data['Pigtail slot'] is not None
                else None,
                'PT_PIN': data['Pigtail pin'] if data['Pigtail pin'] is not None
                else None
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


##########################
# Signal ID replacements #
##########################

# Deal with differential pairs.
for jp in pt_descr.keys():
    for idx, pt in filter(
            lambda x: x[1]['Signal ID'] is not None and (
                x[1]['Signal ID'].endswith('SCL_N') or
                x[1]['Signal ID'].endswith('SDA_N') or
                x[1]['Signal ID'].endswith('RESET_N')
            ),
            enumerate(pt_descr[jp])
    ):
        reference_id = pt['Signal ID'][:-1] + 'P'

        for pt_ref in filter(
                lambda x: x['Signal ID'] == reference_id and
                x['SEAM pin'] is not None,
                pt_descr[jp]
        ):
            jd = pt_ref['DCB slot']

            for dcb in dcb_descr[jd]:
                if pt_ref['SEAM pin'] == dcb['SEAM pin'] and \
                   dcb['Pigtail slot'] is not None and \
                   dcb['Pigtail slot'] == jp and \
                   pt_ref['Pigtail pin'] == dcb['Pigtail pin']:
                    # Modify pt_descr in place.
                    pt_descr[jp][idx]['Signal ID'] = \
                        jd + '_' + dcb['Signal ID'] + '_N'
                    break
            break


# Second, replace 'Signal ID' to DCB side definitions.
for pt_id in range(0, len(pt_descr)):
    for pt_entry in pt_descr[pt_id]:
        if pt_entry['DCB slot'] is not None:
            dcb_id = RulePD.DCBID(pt_entry['DCB slot'])
            for dcb_entry in dcb_descr[int(dcb_id)]:
                if pt_entry['SEAM pin'] == dcb_entry['SEAM pin'] \
                        and \
                        dcb_entry['Pigtail slot'] is not None \
                        and \
                        str(pt_id) == RulePD.PTID(dcb_entry['Pigtail slot']) \
                        and \
                        pt_entry['Pigtail pin'] == dcb_entry['Pigtail pin']:
                    pt_entry['Signal ID'] = dcb_entry['Signal ID']
                    break


################
# Apply rules  #
################

pt_rules = [
    # RulePT_PathFinder(),
    RulePT_PTSingleToDiffP(),
    RulePT_PTSingleToDiffN(),
    RulePT_UnusedToGND(),
    RulePT_NotConnected(),
    RulePT_DCB(),
    RulePT_PTLvSource(brkoutbrd_pin_assignments),
    RulePT_PTLvReturn(brkoutbrd_pin_assignments),
    RulePT_PTLvSense(brkoutbrd_pin_assignments),
    RulePT_PTThermistor(brkoutbrd_pin_assignments),
    RulePT_Default()
]

PtSelector = SelectorPD(pt_descr, pt_rules)
pt_result = PtSelector.do()

dcb_rules = [
    RuleDCB_GND(),
    RuleDCB_AGND(),
    RuleDCB_PTSingleToDiff(),
    RuleDCB_PT(),
    RuleDCB_1V5(brkoutbrd_pin_assignments),
    RuleDCB_2V5(brkoutbrd_pin_assignments),
    RuleDCB_1V5Sense(brkoutbrd_pin_assignments),
    RuleDCB_Default()
]

DcbSelector = SelectorPD(dcb_descr, dcb_rules)
dcb_result = DcbSelector.do()


######################################################################
# Generate an auxiliary dict to aid True/Mirror-type list generation #
######################################################################

dcb_aux = {
    (node.DCB, node.DCB_PIN): (node, prop)
    for (node, prop) in dcb_result.items()
}

for i in range(0, 12):
    # These are power-related, after all.
    brkoutbrd_pin_assignments.append('JD' + str(i) + '_' + 'GND')
    brkoutbrd_pin_assignments.append('JD' + str(i) + '_' + 'AGND')
    # Account for unused pins
    brkoutbrd_pin_assignments.append('JD' + str(i) + '_' + 'B1')
    brkoutbrd_pin_assignments.append('JD' + str(i) + '_' + 'B3')


############################################
# Generate True-type backplane Altium list #
############################################

dcb_result_true = dict()
pt_result_true = dict()
pt_aux_true_type = dict()

# Do DCB slot swapping on DCB side first. The order matters.
for node in dcb_result.keys():
    target_jd = jd_swapping_true[node.DCB]
    target_node, target_prop = dcb_aux[(target_jd, node.DCB_PIN)]

    # Replace all pin definitions with target ones if it is not power-related
    if target_prop['NETNAME'] not in brkoutbrd_pin_assignments:
        key = NetNode(node.DCB, node.DCB_PIN,
                      target_node.PT, target_node.PT_PIN)
        try:
            jd, some_conn, signal = split_netname(target_prop['NETNAME'])
            target_prop['NETNAME'] = node.DCB + '_' + some_conn + '_' + signal
            # Fill up the additional auxiliary dict, for True-type.
            pt_aux_true_type[(target_node.PT, target_node.PT_PIN)] = \
                (key, target_prop)
        except Exception:
            pass

        dcb_result_true[key] = target_prop

    else:
        dcb_result_true[node] = dcb_result[node]

# Now do DCB slot swapping on PT side.
for node in pt_result.keys():
    if (node.PT, node.PT_PIN) in pt_aux_true_type.keys():
        key, target_prop = pt_aux_true_type[(node.PT, node.PT_PIN)]
        pt_result_true[key] = target_prop

    else:
        try:
            prop = pt_result[node]
            jd, some_conn, signal = split_netname(prop['NETNAME'])
            prop['NETNAME'] = jd_swapping_true[jd] + '_' + some_conn + '_' + signal
            key = NetNode(jd_swapping_true[jd], node.DCB_PIN,
                          node.PT, node.PT_PIN)
            pt_result_true[key] = prop
        except Exception:
            pt_result_true[node] = pt_result[node]

write_to_csv(pt_true_result_output_filename, pt_result_true)
write_to_csv(dcb_true_result_output_filename, dcb_result_true)
