#!/usr/bin/env python
#
# License: MIT
# Last Change: Mon Oct 01, 2018 at 01:18 PM -0400

import yaml

from pathlib import Path

from pyUTM.io import XLReader, write_to_csv
from pyUTM.io import flatten, transpose
from pyUTM.selection import SelectorPD, RulePD
from pyUTM.datatype import GenericNetNode
from pyUTM.datatype import ExcelCell
from pyUTM.legacy import legacy_csv_line_dcb

input_dir = Path('input')
output_dir = Path('output')

brkoutbrd_filename = input_dir / Path('brkoutbrd_pin_assignments.yml')
pt_filename = input_dir / Path(
    'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.2.xlsm')
dcb_filename = input_dir / Path(
    'backplaneMapping_SEAMPins_trueType_v5.2.xlsm')

pt_result_output_filename = output_dir / Path('AltiumNetlist_PT_Full_TrueType.csv')
dcb_result_output_filename = output_dir / Path('AltiumNetlist_DCB_Full_TrueType.csv')


############################################
# Read pin assignments from breakout board #
############################################

with open(brkoutbrd_filename) as yaml_file:
    brkoutbrd_pin_assignments_yaml = yaml.safe_load(yaml_file)

# We intent to keep 'Signal ID' only, in a list.
brkoutbrd_pin_assignments = []
for connector in brkoutbrd_pin_assignments_yaml.keys():
    data = transpose(flatten(brkoutbrd_pin_assignments_yaml[connector]))
    signals = [s for s in data['Signal ID'] if s is not None and s != 'GND']
    brkoutbrd_pin_assignments += signals


##########################
# Read info from PigTail #
##########################

PtReader = XLReader(pt_filename)
pt_descr = PtReader.read(range(0, 12), 'B5:K405',
                         sortby=lambda d: d['Pigtail pin'])


######################
# Read info from DCB #
######################

DcbReader = XLReader(dcb_filename)
dcb_descr = DcbReader.read(range(0, 12), 'B5:K405',
                           sortby=lambda d: RulePD.PADDING(d['SEAM pin']))


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
                'DCB': None,
                'DCB_PIN': None,
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
                'DCB': None,
                'DCB_PIN': None,
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
                'DCB': None,
                'DCB_PIN': None,
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
                'DCB': None,
                'DCB_PIN': None,
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


# This rule is a last resort if Tom cannot correct his netnames.
# Should NOT be used normally.
class RulePT_LVSenseGND(RulePD):
    def match(self, data, pt_idx):
        if 'LV_SENSE_GND' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, pt_idx):
        net_name = \
            self.PT_PREFIX + str(pt_idx) + \
            data['Pigtail pin'] + '_' + \
            data['Signal ID']
        return (
            {
                'DCB': None,
                'DCB_PIN': None,
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


# Put PTSingleToDiff rule above the general PTDCB rule
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
                'DCB': None,
                'DCB_PIN': None,
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': net_name, 'ATTR': None}
        )


class RulePT_UnusedToGND(RulePD):
    def match(self, data, pt_idx):
        if data['Signal ID'] is not None \
                and data['Signal ID'].font_color is not None \
                and data['Signal ID'].font_color.tint != 0.0 \
                and data['Signal ID'].font_color.theme == 0:
            return True
        else:
            return False

    def process(self, data, pt_idx):
        return (
            {
                'DCB': None,
                'DCB_PIN': None,
                'PT': self.PT_PREFIX + str(pt_idx),
                'PT_PIN': self.DEPADDING(data['Pigtail pin'])
            },
            {'NETNAME': 'GND', 'ATTR': None}
        )


pt_rules = [
    # RulePT_PathFinder(),
    RulePT_PTSingleToDiffP(),
    RulePT_PTSingleToDiffN(),
    RulePT_UnusedToGND(),
    # RulePT_LVSenseGND(),
    RulePT_NotConnected(),
    RulePT_DCB(),
    RulePT_PTLvSource(brkoutbrd_pin_assignments),
    RulePT_PTLvReturn(brkoutbrd_pin_assignments),
    RulePT_PTLvSense(brkoutbrd_pin_assignments),
    RulePT_PTThermistor(brkoutbrd_pin_assignments),
    RulePT_Default()
]


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
                'PT': None,
                'PT_PIN': None,
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
                'PT': None,
                'PT_PIN': None
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


# Put PTSingleToDiff rule above the general PTDCB rule
class RuleDCB_PTSingleToDiff(RulePD):
    def match(self, data, dcb_idx):
        if 'HYB_i2C' in data['Signal ID'] or \
                'EC_RESET' in data['Signal ID'] or \
                'EC_ADC' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        if 'EC_ADC' in data['Signal ID']:
            # Becuase EC_ADC connects to Thermistor, add prefix THERM
            net_name = \
                self.DCB_PREFIX + self.DCBID(data['DCB slot']) + '_' + \
                self.PT_PREFIX + str(dcb_idx) + '_THERM_' + \
                data['Signal ID'] + '_P'
        else:
            net_name = \
                self.DCB_PREFIX + self.DCBID(data['DCB slot']) + '_' + \
                self.PT_PREFIX + str(dcb_idx) + '_' + \
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


class RuleDCB_DCB(RulePD):
    def match(self, data, dcb_idx):
        if data['SEAM pin D'] is not None:
            # Which means that this DCB pin is connected to a DCB pin.
            return True
        else:
            return False

    def process(self, data, dcb_idx):
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + \
            self.DCB_PREFIX + self.DCBID(data['SEAM slot']) + '_' + \
            data['Signal ID']
        return (
            GenericNetNode(
                self.DCB_PREFIX + str(dcb_idx),
                data['SEAM pin'],
                self.DCB_PREFIX + self.DCBID(data['SEAM slot']),
                self.DEPADDING(data['SEAM pin D'])
            ),
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
                'PT': None,
                'PT_PIN': None
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
                'PT': None,
                'PT_PIN': None
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
                'PT': None,
                'PT_PIN': None
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
        net_name = \
            self.DCB_PREFIX + str(dcb_idx) + '_' + \
            data['Signal ID']
        return (
            {
                'DCB': self.DCB_PREFIX + str(dcb_idx),
                'DCB_PIN': data['SEAM pin'],
                'PT': None,
                'PT_PIN': None
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


dcb_rules = [
    RuleDCB_GND(),
    RuleDCB_AGND(),
    RuleDCB_PT(),
    RuleDCB_1V5(brkoutbrd_pin_assignments),
    RuleDCB_2V5(brkoutbrd_pin_assignments),
    RuleDCB_1V5Sense(brkoutbrd_pin_assignments),
    RuleDCB_DCB(),
    RuleDCB_Default()
]


####################################
# Generate Altium list for PigTail #
####################################

# First, deal with differential pairs.
for pt_id in range(0, len(pt_descr)):
    for pt_entry in pt_descr[pt_id]:
        if pt_entry['Signal ID'] is not None and (
           pt_entry['Signal ID'].endswith('SCL_N') or
           pt_entry['Signal ID'].endswith('SDA_N') or
           pt_entry['Signal ID'].endswith('RESET_N')):
            reference_id = pt_entry['Signal ID'][:-1] + 'P'
            for pt_entry_ref in pt_descr[pt_id]:
                if pt_entry_ref['Signal ID'] == reference_id:
                    if pt_entry_ref['SEAM pin'] is not None:
                        dcb_id = RulePD.DCBID(pt_entry_ref['DCB slot'])
                        for dcb_entry in dcb_descr[int(dcb_id)]:
                            if pt_entry_ref['SEAM pin'] == dcb_entry['SEAM pin'] and\
                               dcb_entry['Pigtail slot'] is not None and\
                               str(pt_id) == RulePD.PTID(dcb_entry['Pigtail slot']) and\
                               pt_entry_ref['Pigtail pin'] == dcb_entry['Pigtail pin']:
                                pt_entry['Signal ID'] = \
                                        ExcelCell(
                                        "JD"+str(dcb_id)+'_'+dcb_entry['Signal ID']+'_N'
                                        )
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

# Now apply all rules defined in the previous section
PtSelector = SelectorPD(pt_descr, pt_rules)
print('====WARNINGS for PigTail====')
pt_result = PtSelector.do()

# Finally, write to csv file
write_to_csv(pt_result_output_filename, pt_result)


################################
# Generate Altium list for DCB #
################################

DcbSelector = SelectorPD(dcb_descr, dcb_rules)
print('====WARNINGS for DCB====')
dcb_result = DcbSelector.do()

write_to_csv(dcb_result_output_filename, dcb_result,
             formatter=legacy_csv_line_dcb)
