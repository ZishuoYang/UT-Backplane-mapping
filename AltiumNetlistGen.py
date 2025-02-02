#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 19, 2019 at 05:33 PM -0500

from pathlib import Path
from collections import defaultdict
from copy import deepcopy

import re
import sys
sys.path.insert(0, './pyUTM')

from pyUTM.io import write_to_file, write_to_csv
from pyUTM.io import csv_line
from pyUTM.io import YamlReader
from pyUTM.io import prepare_descr_for_xlsx_output, XLWriter
from pyUTM.selection import SelectorPD, RulePD
from pyUTM.datatype import NetNode
from pyUTM.common import flatten, transpose
from pyUTM.common import jd_swapping_true
from pyUTM.common import jd_swapping_mirror, jp_swapping_mirror
from pyUTM.legacy import PADDING

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

pt_mirror_output_filename = output_dir / Path(
    'AltiumNetlist_PT_Full_MirrorType.csv')
dcb_mirror_output_filename = output_dir / Path(
    'AltiumNetlist_DCB_Full_MirrorType.csv')
pt_result_mirror_depop_aux_output_filename = output_dir / Path(
    'AuxList_PT_Full_MirrorType.csv'
)

pt_true_excel_file = output_dir / Path('Mapping_PT_TrueType.xlsx')
dcb_true_excel_file = output_dir / Path('Mapping_DCB_TrueType.xlsx')
pt_mirror_excel_file = output_dir / Path('Mapping_PT_MirrorType.xlsx')
dcb_mirror_excel_file = output_dir / Path('Mapping_DCB_MirrorType.xlsx')


###########
# Helpers #
###########

# Netname matching #############################################################

def check_diff_pairs_notes(pt_descr):
    for jp in pt_descr.keys():
        for pt in pt_descr[jp]:
            reference_id = pt['Signal ID'][:-1] + 'P'

            for pt_ref in filter(lambda x: x['Signal ID'] == reference_id and
                                 x['SEAM pin'] is not None,
                                 pt_descr[jp]):

                # Quick and dirty error check to make sure both ends of the same
                # differential pair are treated the same.
                if pt['Note'] != pt_ref['Note']:
                    raise ValueError('The following differential pair has different notes: {}, {}'.format(
                        pt_ref['Signal ID'], pt['Signal ID']
                    ))


def match_diff_pairs(pt_descr, dcb_descr, net_name_ending):
    for jp in pt_descr.keys():
        for idx, pt in filter(
                lambda x: x[1]['Signal ID'] is not None and
                x[1]['Signal ID'].endswith(net_name_ending),
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
            # We always keep the original signal ID for Excel output
            pt['Original Signal ID'] = pt['Signal ID']
            if pt['DCB slot'] is not None:
                jd = pt['DCB slot']
                for dcb in dcb_descr[jd]:
                    # Also add note entry for DCB to record depopulation info
                    dcb['Note'] = None

                    if pt['SEAM pin'] == dcb['SEAM pin'] and \
                            dcb['Pigtail slot'] is not None and \
                            dcb['Pigtail slot'] == jp and \
                            pt['Pigtail pin'] == dcb['Pigtail pin']:
                        pt['Signal ID'] = dcb['Signal ID']
                        dcb['Note'] = pt['Note']
                        break


# Output #######################################################################

def aux_dict_gen(
        pt_result,
        depopulation_keywords=[
            'ELK', 'RCLK', 'TFC', 'HYB', 'LV_SOURCE', 'LV_RETURN', 'LV_SENSE',
            'THERM'
        ],
        inclusive_keywords=[
            'EC_RESET', 'EC_HYB_i2C', 'LV_SENSE_GND'
        ]
):
    result = defaultdict(lambda: defaultdict(dict))

    for node, prop in pt_result.items():
        if prop['NOTE'] is not None and 'Alpha only' in prop['NOTE']:
            for kw in depopulation_keywords:
                if kw in prop['NETNAME']:
                    result[node.PT]['Depopulation: {}'.format(kw)][node] = prop
                    break

        for kw in inclusive_keywords:
            if kw in prop['NETNAME']:
                result[node.PT]['All: {}'.format(kw)][node] = prop

    return result


def aux_output_gen(aux_dict, title):
    output = [title]

    for jp, sections in sorted(aux_dict.items()):
        output.append('# '+jp)
        for title, data in sorted(sections.items()):
            output.append('## '+title)
            for node, prop in data.items():
                output.append(csv_line(node, prop))
            output.append('')

    return output


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

# Read info from Pigtail #
PtReader = YamlReader(pt_filename)
pt_descr = PtReader.read(flattener=lambda x: flatten(x, 'Pigtail pin'))

# Read info from DCB #
DcbReader = YamlReader(dcb_filename)
dcb_descr = DcbReader.read(flattener=lambda x: flatten(x, 'SEAM pin'))

# Make sure two ends of a single differential pair have the same note.
check_diff_pairs_notes(pt_descr)


########################################
# Define rules for Pigtail Altium list #
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
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = dcb_name + '_' + jp + '_THERM_' + tail
        else:
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


# This needs to be placed above RulePT_NotConnected
class RulePT_PTThermistorSpecial(RulePD):
    def match(self, data, jp):
        if data['Note'] is not None and 'Therm to JT' in data['Note']:
            return True
        else:
            return False

    def process(self, data, jp):
        netname = jp + '_' + self.find_jt(jp) + '_' + data['Signal ID'].replace(
            'THERMISTOR', 'THERM')
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen(netname, data['Note']))

    @staticmethod
    def find_jt(jp):
        jp_idx = int(jp[2:])
        if jp_idx < 4:
            return 'JT0'
        elif jp_idx < 8:
            return 'JT1'
        else:
            return 'JT2'


class RulePT_PTLvSenseGnd(RulePD):
    def match(self, data, jp):
        if 'LV_SENSE_GND' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, jp):
        net_name = jp + PADDING(data['Pigtail pin']) + '_' + data['Signal ID']
        return (
            NetNode(PT=jp, PT_PIN=data['Pigtail pin']),
            self.prop_gen(net_name, data['Note'], None))


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
            if 'DC' in data['Signal ID'] or \
                    'SEC_DIN' in data['Signal ID'] or \
                    'EC_SEC_CLK' in data['Signal ID']:
                return True

    def process(self, data, jd):
        if 'SEC_DIN' in data['Signal ID'] or 'EC_SEC_CLK' in data['Signal ID']:
            net_name = jd + '_SEC_ELK_' + data['Signal ID'][-1]
        else:
            net_name = jd + '_ELK_' + data['Signal ID'][-1]
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen(net_name, attr='_FRO_'))


# This needs to be placed SECOND to the end of the rules list.  It only selects
# entries that should become FRO AND are REMOTE_RESETB
class RuleDCB_REMOTE_RESET(RulePD):
    def match(self, data, jd):
        if 'REMOTE_RESETB' in data['Signal ID']:
            return True

    def process(self, data, jd):
        net_name = jd + '_' + data['Signal ID']
        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin']),
            self.prop_gen(net_name))


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


class RuleDCB_RefToSense(RulePD):
    def match(self, data, jd):
        if 'EC_ADC_REF' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, jd):
        jp = jd.replace('D', 'P')
        signal = data['Signal ID']

        if 'REF13' in signal:
            jp_pin = 'A16'
            net_name = jp + jp_pin + '_' + 'P3_LV_SENSE_GND'
        elif 'REF14' in signal:
            jp_pin = 'J24'
            net_name = jp + jp_pin + '_' + 'P1_WEST_LV_SENSE_GND'
        elif 'REF15' in signal:
            # NOTE: This is a special case, because in the netname, the pin
            # number is padded!
            jp_pin = 'F5'
            net_name = jp + 'F05' + '_' + 'P2_EAST_LV_SENSE_GND'
        else:
            raise ValueError(
                'EC_ADC_REF: {} detected but not belongs to any known case'.format(
                    signal
                ))

        return (
            NetNode(DCB=jd, DCB_PIN=data['SEAM pin'], PT=jp, PT_PIN=jp_pin),
            self.prop_gen(net_name))


######################
# Proto -> True-type #
######################

dcb_descr_true = {jd: dcb_descr[jd_swapping_true[jd]]
                  for jd in dcb_descr.keys()}

pt_descr_true = deepcopy(pt_descr)

for jp in pt_descr_true.keys():
    for pt in pt_descr_true[jp]:
        if pt['DCB slot'] is not None:
            pt['DCB slot'] = jd_swapping_true[pt['DCB slot']]

# Deal with differential pairs.
match_diff_pairs(pt_descr_true, dcb_descr_true, 'SCL_N')
match_diff_pairs(pt_descr_true, dcb_descr_true, 'SDA_N')
match_diff_pairs(pt_descr_true, dcb_descr_true, 'RESET_N')
match_diff_pairs(pt_descr_true, dcb_descr_true, 'THERMISTOR_N')

# Replace 'Signal ID' to DCB side definitions.
match_dcb_side_signal_id(pt_descr_true, dcb_descr_true)


############################################
# Define rules to be applied to True-type  #
############################################

# Define an alias to indicate that here we are dealing with true-type.
brkoutbrd_pin_assignments_true = brkoutbrd_pin_assignments

pt_rules_true = [
    RulePT_PTSingleToDiffP(),
    RulePT_PTSingleToDiffN(),
    RulePT_UnusedToGND(),
    RulePT_PTLvSenseGnd(),
    RulePT_PTThermistorSpecial(),
    RulePT_DCB(),
    RulePT_PTLvSource(brkoutbrd_pin_assignments_true),
    RulePT_PTLvReturn(brkoutbrd_pin_assignments_true),
    RulePT_PTLvSense(brkoutbrd_pin_assignments_true),
    RulePT_Default()
]

dcb_rules_true = [
    RuleDCB_GND(),
    RuleDCB_AGND(),
    RuleDCB_RefToSense(),
    RuleDCB_PTSingleToDiff(),
    RuleDCB_PT(),
    RuleDCB_1V5(brkoutbrd_pin_assignments_true),
    RuleDCB_2V5(brkoutbrd_pin_assignments_true),
    RuleDCB_1V5Sense(brkoutbrd_pin_assignments_true),
    RuleDCB_FRO_ELK(),
    RuleDCB_REMOTE_RESET(),
    RuleDCB_Default()
]


############################################
# Generate True-type backplane Altium list #
############################################

# Debug
# for rule in pt_rules_true:
#     rule.debug_node = NetNode('JD1', 'C3', 'JP0', 'F8')

PtSelectorTrue = SelectorPD(pt_descr_true, pt_rules_true)
pt_result_true = PtSelectorTrue.do()

DcbSelectorTrue = SelectorPD(dcb_descr_true, dcb_rules_true)
dcb_result_true = DcbSelectorTrue.do()

# See if we have any unused rule
# for rule in pt_rules+dcb_rules:
#     print('The rule {} has been used {} times'.format(
#         rule.__class__.__name__, rule.counter))

write_to_csv(pt_true_output_filename, pt_result_true, csv_line)
write_to_csv(dcb_true_output_filename, dcb_result_true, csv_line)


###############################################
# Generate True-type backplane auxiliary list #
###############################################

pt_result_true_depop_aux = aux_dict_gen(pt_result_true)

write_to_file(pt_result_true_depop_aux_output_filename,
              aux_output_gen(pt_result_true_depop_aux,
                             'Aux PT list for True-type'))


########################
# Proto -> Mirror-type #
########################

# NOTE: We don't want to modify the content of dcb_descr in-place.
dcb_descr_copy = deepcopy(dcb_descr)
jd_swapping_mirror_inverse = {v: k for k, v in jd_swapping_mirror.items()}
dcb_descr_mirror = {jd: dcb_descr_copy[jd_swapping_mirror_inverse[jd]]
                    for jd in dcb_descr_copy.keys()}

for jd in dcb_descr_mirror.keys():
    for dcb in dcb_descr_mirror[jd]:
        if dcb['Pigtail slot'] is not None:
            dcb['Pigtail slot'] = jp_swapping_mirror[dcb['Pigtail slot']]

# NOTE: We don't want to modify the content of pt_descr in-place.
pt_descr_copy = deepcopy(pt_descr)
pt_descr_mirror = {jp: pt_descr_copy[jp_swapping_mirror[jp]]
                   for jp in pt_descr_copy.keys()}

for jp in pt_descr_mirror.keys():
    for pt in pt_descr_mirror[jp]:
        if pt['DCB slot'] is not None:
            pt['DCB slot'] = jd_swapping_mirror[pt['DCB slot']]

# Deal with differential pairs.
match_diff_pairs(pt_descr_mirror, dcb_descr_mirror, 'SCL_N')
match_diff_pairs(pt_descr_mirror, dcb_descr_mirror, 'SDA_N')
match_diff_pairs(pt_descr_mirror, dcb_descr_mirror, 'RESET_N')
match_diff_pairs(pt_descr_mirror, dcb_descr_mirror, 'THERMISTOR_N')

# Replace 'Signal ID' to DCB side definitions.
match_dcb_side_signal_id(pt_descr_mirror, dcb_descr_mirror)


##############################################
# Define rules to be applied to Mirror-type  #
##############################################

brkoutbrd_pin_assignments_mirror = []
# Swap a few hybrid power signals due to #(active hybrids) diff on Mirror
for signal in brkoutbrd_pin_assignments_true:
    hyb = re.match(r'(^JP\d+)_(JPU\d|JPL\d|JT\d)_(P2_WEST|P4).*', signal)
    if hyb is not None and (
            (hyb.group(3) == 'P4' and hyb.group(1).endswith(
                ('4', '7', '8', '11'))
             ) or
            (hyb.group(3) == 'P2_WEST' and hyb.group(1).endswith(
                ('1', '2'))
             )
    ):
        signal = re.sub(hyb.group(1), jp_swapping_mirror[hyb.group(1)], signal)
        brkoutbrd_pin_assignments_mirror.append(signal)

    else:
        brkoutbrd_pin_assignments_mirror.append(signal)

pt_rules_mirror = [
    RulePT_PTSingleToDiffP(),
    RulePT_PTSingleToDiffN(),
    RulePT_UnusedToGND(),
    RulePT_PTLvSenseGnd(),
    RulePT_PTThermistorSpecial(),
    RulePT_DCB(),
    RulePT_PTLvSource(brkoutbrd_pin_assignments_mirror),
    RulePT_PTLvReturn(brkoutbrd_pin_assignments_mirror),
    RulePT_PTLvSense(brkoutbrd_pin_assignments_mirror),
    RulePT_Default()
]

dcb_rules_mirror = [
    RuleDCB_GND(),
    RuleDCB_AGND(),
    RuleDCB_RefToSense(),
    RuleDCB_PTSingleToDiff(),
    RuleDCB_PT(),
    RuleDCB_1V5(brkoutbrd_pin_assignments_mirror),
    RuleDCB_2V5(brkoutbrd_pin_assignments_mirror),
    RuleDCB_1V5Sense(brkoutbrd_pin_assignments_mirror),
    RuleDCB_FRO_ELK(),
    RuleDCB_REMOTE_RESET(),
    RuleDCB_Default()
]


##############################################
# Generate Mirror-type backplane Altium list #
##############################################

# Debug
# for rule in pt_rules_mirror:
#     rule.debug_node = NetNode(None, None, 'JP2', 'A35')

PtSelectorMirror = SelectorPD(pt_descr_mirror, pt_rules_mirror)
pt_result_mirror = PtSelectorMirror.do()

DcbSelectorMirror = SelectorPD(dcb_descr_mirror, dcb_rules_mirror)
dcb_result_mirror = DcbSelectorMirror.do()

write_to_csv(pt_mirror_output_filename, pt_result_mirror, csv_line)
write_to_csv(dcb_mirror_output_filename, dcb_result_mirror, csv_line)


#################################################
# Generate Mirror-type backplane auxiliary list #
#################################################

pt_result_mirror_depop_aux = aux_dict_gen(pt_result_mirror)

write_to_file(pt_result_mirror_depop_aux_output_filename,
              aux_output_gen(pt_result_mirror_depop_aux,
                             'Aux PT list for Mirror-type'))


#################################
# Write mappings to Excel files #
#################################

PtTrueWriter = XLWriter(pt_true_excel_file)
PtTrueWriter.write(prepare_descr_for_xlsx_output(pt_descr_true))

DcbTrueWriter = XLWriter(dcb_true_excel_file)
DcbTrueWriter.write(prepare_descr_for_xlsx_output(dcb_descr_true))

PtMirrorWriter = XLWriter(pt_mirror_excel_file)
PtMirrorWriter.write(prepare_descr_for_xlsx_output(pt_descr_mirror))

DcbMirrorWriter = XLWriter(dcb_mirror_excel_file)
DcbMirrorWriter.write(prepare_descr_for_xlsx_output(dcb_descr_mirror))
