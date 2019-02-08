#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Jan 23, 2019 at 03:17 PM -0500

from pathlib import Path
from copy import deepcopy

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.io import write_to_csv, write_to_file
from pyUTM.io import YamlReader
from pyUTM.selection import SelectorPD, RulePD
from pyUTM.datatype import NetNode
from pyUTM.common import flatten, transpose
from pyUTM.common import jd_swapping_true

input_dir = Path('input')
output_dir = Path('output')

brkoutbrd_filename = input_dir / Path('brkoutbrd_pin_assignments.yml')
pt_filename = input_dir / Path('backplane_mapping_PT.yml')
dcb_filename = input_dir / Path('backplane_mapping_DCB.yml')

pt_true_output_filename = output_dir / Path(
    'AltiumNetlist_PT_Full_TrueType.csv')
dcb_true_output_filename = output_dir / Path(
    'AltiumNetlist_DCB_Full_TrueType.csv')
pt_result_true_depop_aux_output_filename = output_dir / Path(
    'AuxList_PT_Full_TrueType.csv'
)


###########
# Helpers #
###########

def match_diff_pairs(pt_descr, dcb_descr):
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
                        pt_descr[jp][idx]['DCB slot'] = jd
                        break
                break


def match_dcb_side_signal_id(pt_descr, dcb_descr):
    for jp in pt_descr.keys():
        for pt in pt_descr[jp]:
            if pt['DCB slot'] is not None:
                jd = pt['DCB slot']
                for dcb in dcb_descr[jd]:
                    if pt['SEAM pin'] == dcb['SEAM pin'] and \
                            dcb['Pigtail slot'] is not None and \
                            dcb['Pigtail slot'] == jp and \
                            pt['Pigtail pin'] == dcb['Pigtail pin']:
                        pt['Signal ID'] = dcb['Signal ID']
                        break


def aux_list_gen(pt_result):
    result = {'JP'+str(i): {
        'Depopulation: ELK': {},
        'Depopulation: RCLK': {},
        'Depopulation: MC_TFC': {},
        'Depopulation: HYB': {},
        'Depopulation: LV_SOURCE': {},
        'Depopulation: LV_RETURN': {},
        'Depopulation: LV_SENSE_GND': {},
        'Depopulation: LV_SENSE_N/P': {},
        'Depopulation: THERM': {},
        'Depopulation: EC_RESET': {},
        'All: EC_RESET': {},
        'All: EC_HYB_i2C': {},
        'All: LV_SENSE_GND': {},
    } for i in range(0, 12)}

    for node in pt_result:
        prop = pt_result[node]
        if prop['NOTE'] == 'Alpha only':
            if 'ELK' in prop['NETNAME']:
                result[node.PT]['Depopulation: ELK'][node] = prop
            elif 'RCLK' in prop['NETNAME']:
                result[node.PT]['Depopulation: RCLK'][node] = prop
            elif 'TFC' in prop['NETNAME']:
                result[node.PT]['Depopulation: MC_TFC'][node] = prop
            elif 'HYB' in prop['NETNAME']:
                result[node.PT]['Depopulation: HYB'][node] = prop
            elif 'LV_SOURCE' in prop['NETNAME']:
                result[node.PT]['Depopulation: LV_SOURCE'][node] = prop
            elif 'LV_RETURN' in prop['NETNAME']:
                result[node.PT]['Depopulation: LV_RETURN'][node] = prop
            elif 'LV_SENSE_GND' in prop['NETNAME']:
                result[node.PT]['Depopulation: LV_SENSE_GND'][node] = prop
            elif 'LV_SENSE' in prop['NETNAME']:
                result[node.PT]['Depopulation: LV_SENSE_N/P'][node] = prop
            elif 'THERM' in prop['NETNAME']:
                result[node.PT]['Depopulation: THERM'][node] = prop
            else:
                result[node.PT]['Depopulation: EC_RESET'][node] = prop

        if 'EC_RESET' in prop['NETNAME']:
            result[node.PT]['All: EC_RESET'][node] = prop

        if 'EC_HYB_i2C' in prop['NETNAME']:
            result[node.PT]['All: EC_HYB_i2C'][node] = prop

        if 'LV_SENSE_GND' in prop['NETNAME']:
            result[node.PT]['All: LV_SENSE_GND'][node] = prop

    return result


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
    def match(self, data, jp):
        return True

    def process(self, data, jp):
        net_name = jp + '_' + data['Signal ID']
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen(net_name, data['Note'], '_FRO_'))


class RulePT_PathFinder(RulePD):
    def match(self, data, jp):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if jp in ['JP0', 'JP1']:
            return False

        # For path finder, skip non-BOB nets when not in slot 0 or 1
        keywords = ['LV_SOURCE', 'LV_RETURN', 'LV_SENSE', 'THERMISTOR']
        result = [False if kw in data['Signal ID'] else True for kw in keywords]
        return self.AND(result)

    def process(self, data, jp):
        # Note: here the matching nodes will have placeholder in netlist file.
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen(None, data['Note'], '_PlaceHolder_'))


class RulePT_DCB(RulePD):
    def match(self, data, jp):
        if data['SEAM pin'] is not None:
            # Which means that this PT pin is connected to a DCB pin.
            return True
        else:
            return False

    def process(self, data, jp):
        net_name = data['DCB slot'] + '_' + jp + '_' + data['Signal ID']
        return (
            NetNode(DCB=data['DCB slot'], DCB_PIN=data['SEAM pin'],
                    PT=jp, PT_PIN=data['Pigtail pin']
                    ),
            self.prop_gen(net_name, data['Note']))


class RulePT_NotConnected(RulePD):
    def match(self, data, jp):
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

    def process(self, data, jp):
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen('GND', data['Note']))


class RulePT_PTLvSource(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, jp):
        if 'LV_SOURCE' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, jp):
        net_name = jp + '_' + data['Signal ID']
        attr = '_FRO_'

        for rule in self.rules:
            pt_name, tail = rule.split('_', 1)
            if jp == pt_name and data['Signal ID'] in tail:
                net_name = rule
                attr = None
                break
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen(net_name, data['Note'], attr))


class RulePT_PTLvReturn(RulePT_PTLvSource):
    def match(self, data, jp):
        if 'LV_RETURN' in data['Signal ID']:
            return True
        else:
            return False


class RulePT_PTLvSense(RulePT_PTLvSource):
    def match(self, data, jp):
        if 'LV_SENSE' in data['Signal ID']:
            return True
        else:
            return False


class RulePT_PTThermistor(RulePT_PTLvSource):
    def match(self, data, jp):
        if 'THERMISTOR' in data['Signal ID']:
            return True
        else:
            return False


# Put PTSingleToDiff rule above the general PT-DCB rule
class RulePT_PTSingleToDiffP(RulePD):
    def match(self, data, jp):
        if not data['Signal ID'].endswith('_N') and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, jp):
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = data['DCB slot'] + '_' + jp + '_THERM_' + \
                data['Signal ID'] + '_P'
        else:
            net_name = data['DCB slot'] + '_' + jp + '_' + \
                data['Signal ID'] + '_P'
        return (
            NetNode(DCB=data['DCB slot'], DCB_PIN=data['SEAM pin'],
                    PT=jp, PT_PIN=data['Pigtail pin']
                    ),
            self.prop_gen(net_name, data['Note']))


class RulePT_PTSingleToDiffN(RulePD):
    def match(self, data, jp):
        if data['Signal ID'].endswith('_N') and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, jp):
        dcb_name, tail = data['Signal ID'].split('_', 1)
        net_name = dcb_name + '_' + jp + '_' + tail
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin'],
                    DCB=data['DCB slot'], DCB_PIN=data['SEAM pin']),
            self.prop_gen(net_name, data['Note']))


class RulePT_UnusedToGND(RulePD):
    def match(self, data, jp):
        if data['Note'] == 'Unused':
            return True
        else:
            return False

    def process(self, data, jp):
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen('GND', data['Note']))


####################################
# Define rules for DCB Altium list #
####################################

# This needs to be placed at the end of the rules list.  It only handles
# entries that are not matched and therfore should become FRO.
class RuleDCB_Default(RulePD):
    def match(self, data, jd):
        return True

    def process(self, data, jd):
        net_name = jd + '_' + data['Signal ID']
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen(net_name, attr='_FRO_'))


# This needs to be placed SECOND to the end of the rules list.  It only selects
# entries that should become FRO AND are ELK input signals (for proper biasing)
class RuleDCB_FRO_ELK(RulePD):
    def match(self, data, jd):
        if 'ELK' in data['Signal ID']:
            # Select GBTx data ELK or secondary-ctrl data-input ELK
            if 'DC' in data['Signal ID'] or '_SEC_DIN_' in data['Signal ID']:
                return True

    def process(self, data, jd):
        net_name = jd + '_FRO_ELK_' + data['Signal ID'][-1]
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen(net_name, attr='_FRO_'))


class RuleDCB_PathFinder(RulePD):
    def match(self, data, jd):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if jd in ['JD0', 'JD2', 'JD4']:
            return False

    def process(self, data, jd):
        # Note: here the matching nodes will have placeholder in netlist file.
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen(None, attr='_PlaceHolder_'))


class RuleDCB_PT(RulePD):
    def match(self, data, jd):
        if data['Pigtail pin'] is not None:
            # Which means that this DCB pin is connected to a PT pin.
            return True
        else:
            return False

    def process(self, data, jd):
        net_name = jd + '_' + data['Pigtail slot'] + '_' + data['Signal ID']
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin'],
                    PT=data['Pigtail slot'], PT_PIN=data['Pigtail pin']
                    ),
            self.prop_gen(net_name))


# Put PTSingleToDiff rule above the general PT-DCB rule
class RuleDCB_PTSingleToDiff(RulePD):
    def match(self, data, jd):
        if data['Pigtail slot'] is not None and \
                ('HYB_i2C' in data['Signal ID'] or
                 'EC_RESET' in data['Signal ID'] or
                 'EC_ADC' in data['Signal ID']):
            return True
        else:
            return False

    def process(self, data, jd):
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = jd + '_' + data['Pigtail slot'] + '_THERM_' \
                + data['Signal ID'] + '_P'
        else:
            net_name = jd + '_' + data['Pigtail slot'] + '_' \
                + data['Signal ID'] + '_P'
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin'],
                    PT=data['Pigtail slot'], PT_PIN=data['Pigtail pin']
                    ),
            self.prop_gen(net_name))


class RuleDCB_1V5(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, jd):
        if data['Signal ID'] == '1.5V':
            return True
        else:
            return False

    def process(self, data, jd):
        net_name = self.netname_replacement(jd, data['Signal ID'])
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin'],),
            self.prop_gen(net_name))

    def netname_replacement(self, jd, signal):
        net_name = jd + '_' + signal
        for rule in self.rules:
            dcb_name, tail = rule.split('_', 1)
            if jd == dcb_name and '1V5' in tail and 'SENSE' not in tail:
                net_name = rule
                break
        return net_name


class RuleDCB_2V5(RuleDCB_1V5):
    def match(self, data, jd):
        if data['Signal ID'] == '2.5V':
            return True
        else:
            return False

    def netname_replacement(self, jd, signal):
        net_name = jd + '_' + signal
        for rule in self.rules:
            if '2V5' in rule and 'SENSE' not in rule:
                dcb1, dcb2, _ = rule.split('_', 2)
                if jd == dcb1 or jd[2:] == dcb2:
                    net_name = rule
                    break
        return net_name


class RuleDCB_1V5Sense(RuleDCB_1V5):
    def match(self, data, jd):
        if '1V5_SENSE' in data['Signal ID']:
            return True
        else:
            return False

    def netname_replacement(self, jd, signal):
        net_name = jd + '_' + signal
        for rule in self.rules:
            dcb_name, tail = rule.split('_', 1)
            if jd == dcb_name and signal[:-2] in tail:
                net_name = rule
                break
        return net_name


class RuleDCB_GND(RulePD):
    def match(self, data, jd):
        if 'GND' == data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, jd):
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen('GND'))


class RuleDCB_AGND(RuleDCB_GND):
    def match(self, data, jd):
        if 'AGND' == data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, jd):
        net_name = jd + '_' + 'AGND'
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin'],
                    PT=data['Pigtail slot'] if data['Pigtail slot'] is not None
                    else None,
                    PT_PIN=data['Pigtail pin'] if data['Pigtail pin'] is not
                    None else None
                    ),
            self.prop_gen(net_name))


###############################
# Define rules to be applied  #
###############################

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

dcb_rules = [
    RuleDCB_GND(),
    RuleDCB_AGND(),
    RuleDCB_PTSingleToDiff(),
    RuleDCB_PT(),
    RuleDCB_1V5(brkoutbrd_pin_assignments),
    RuleDCB_2V5(brkoutbrd_pin_assignments),
    RuleDCB_1V5Sense(brkoutbrd_pin_assignments),
    RuleDCB_FRO_ELK(),
    RuleDCB_Default()
]


###########################################
# True-type signal manipulations (VOODOO) #
###########################################

pt_descr_true = deepcopy(pt_descr)
dcb_descr_true = {}

for jd in dcb_descr.keys():
    dcb_descr_true[jd] = dcb_descr[jd_swapping_true[jd]]

for jp in pt_descr_true.keys():
    for pt in pt_descr_true[jp]:
        if pt['DCB slot'] is not None:
            pt['DCB slot'] = jd_swapping_true[pt['DCB slot']]

# Deal with differential pairs.
match_diff_pairs(pt_descr_true, dcb_descr_true)

# Replace 'Signal ID' to DCB side definitions.
match_dcb_side_signal_id(pt_descr_true, dcb_descr_true)


############################################
# Generate True-type backplane Altium list #
############################################

PtSelector = SelectorPD(pt_descr_true, pt_rules)
pt_result_true = PtSelector.do()

DcbSelector = SelectorPD(dcb_descr_true, dcb_rules)
dcb_result_true = DcbSelector.do()

write_to_csv(pt_true_output_filename, pt_result_true)
write_to_csv(dcb_true_output_filename, dcb_result_true)


###############################################
# Generate True-type backplane auxiliary list #
###############################################

pt_result_true_depop_aux = aux_list_gen(pt_result_true)

# Always clear the content of the output file
write_to_file(pt_result_true_depop_aux_output_filename,
              'Aux PT list for True-type', mode='w')

for jp in pt_result_true_depop_aux.keys():
    write_to_file(pt_result_true_depop_aux_output_filename, '# '+jp)
    for sec in pt_result_true_depop_aux[jp].keys():
        write_to_file(pt_result_true_depop_aux_output_filename, '## '+sec)
        write_to_csv(pt_result_true_depop_aux_output_filename,
                     pt_result_true_depop_aux[jp][sec], mode='a')
        write_to_file(pt_result_true_depop_aux_output_filename, '')
