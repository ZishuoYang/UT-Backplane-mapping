#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 06:20 PM -0400

from os.path import join

from pyUTM.io import XLReader, write_to_csv
from pyUTM.selection import SelectorPD, RulePD

brkoutbrd_filename = join('templates',
                          'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')
pt_filename = join('templates',
                   'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')
dcb_filename = join('templates',
                    'backplaneMapping_SEAMPins_trueType_v4.1.xlsm')
pt_result_output_filename = join('gen', 'AltiumNetlist_PT.csv')


############################################
# Read pin assignments from breakout board #
############################################

BrkReader = XLReader(brkoutbrd_filename)
cell_range_headers = {
    'A4:D18':    {'A': 'left', 'D': 'right'},
    'F4:I18':    {'F': 'left', 'I': 'right'},
    'A55:D69':   {'A': 'left', 'D': 'right'},
    'F55:I69':   {'F': 'left', 'I': 'right'},
    'A106:D120': {'A': 'left', 'D': 'right'},
    'F106:I120': {'F': 'left', 'I': 'right'},
    'K4:N53':    {'K': 'left', 'N': 'right'},
    'K55:N104':  {'K': 'left', 'N': 'right'},
    'K106:N155': {'K': 'left', 'N': 'right'}
}

brkoutbrd_pin_assignments_with_dict = list()
for cell_range in cell_range_headers.keys():
    # Note: 'extend' is used so we won't get a nested list.
    brkoutbrd_pin_assignments_with_dict.extend(
        BrkReader.read(['PinAssignments'], cell_range,
                       headers=cell_range_headers[cell_range])[0]
    )

# Now we get a behemoth list, each entry is a two-key dictionary. We want to
# extract all values that is not 'GND' nor None.
brkoutbrd_pin_assignments = list()
for d in brkoutbrd_pin_assignments_with_dict:
    for key in d.keys():
        if d[key] != 'GND' and d[key] is not None:
            brkoutbrd_pin_assignments.append(d[key])


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
dcb_descr = DcbReader.read(range(0, 12), 'B5:J405',
                           sortby=lambda d: d['SEAM pin'])


########################################
# Define rules for PigTail Altium list #
########################################
# Each of Zishuo's list entry is defined as:
#   ['DCB slot #', 'DCB connector letter pin', 'DCB connector numerical pin',
#    'PT slot #',  'PT connector letter pin',  'PT connector numerical pin',
#    'Signal ID']

# This needs to be placed at the end of the rules list.  It always returns
# 'True' to handle entries NOT matched by any other rules.
class RulePTDefault(RulePD):
    def match(self, data, pt_idx):
        return True

    def process(self, data, pt_idx):
        connection = self.PT_PREFIX + \
            str(pt_idx) + self.PADDING(data['Pigtail pin']) + \
            '_ForRefOnly_' + data['Signal ID']
        return (connection,
                pt_idx, self.PADDING(data['Pigtail pin']),
                None, None)


class RulePTPathFinder(RulePD):
    def match(self, data, pt_idx):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if pt_idx in [0, 1]:
            return False

        # For path finder, skip non-BOB nets when not in slot 0 or 1
        keywords = ['LV_SOURCE', 'LV_RETURN', 'LV_SENSE']
        result = [False if kw in data['Signal ID'] else True for kw in keywords]
        return self.AND(result)

    def process(self, data, pt_idx):
        # Note: here the matching data will NOT be written to netlist file.
        print('WARNING: The following pin is not a LV_* connection!: %s %s'
              % (pt_idx, data['Pigtail pin']))


class RulePTDCB(RulePD):
    def match(self, data, pt_idx):
        if data['DCB slot'] is not None:
            # Which means that this PT pin is connected to a DCB pin.
            return True
        else:
            return False

    def process(self, data, pt_idx):
        connection = self.DCB_PREFIX + \
            self.DCBID(data['DCB slot']) + self.PADDING(data['SEAM pin']) + \
            '_' + self.PT_PREFIX + \
            str(pt_idx) + self.PADDING(data['Pigtail pin']) + \
            '_' + data['Signal ID']
        return (connection,
                pt_idx, self.PADDING(data['Pigtail pin']),
                None, None)


class RulePTPTLvSource(RulePD):
    def __init__(self, brkoutbrd_rules):
        self.rules = brkoutbrd_rules

    def match(self, data, pt_idx):
        if 'LV_SOURCE' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, pt_idx):
        connection = self.PT_PREFIX + \
            str(pt_idx) + self.PADDING(data['Pigtail pin']) + \
            '_ForRefOnly_' + data['Signal ID']
        for i in range(0, len(self.rules)):
            if self.PT_PREFIX+str(pt_idx) in self.rules[i] and \
                    data['Signal ID'] in self.rules[i]:
                connection = self.rules[i]
                break
        return (connection,
                pt_idx, self.PADDING(data['Pigtail pin']),
                None, None)


class RulePTPTLvReturn(RulePTPTLvSource):
    def match(self, data, pt_idx):
        if 'LV_RETURN' in data['Signal ID']:
            return True
        else:
            return False


class RulePTPTLvSense(RulePTPTLvSource):
    def match(self, data, pt_idx):
        if 'LV_SENSE' in data['Signal ID']:
            return True
        else:
            return False


class RulePTPTThermistor(RulePTPTLvSource):
    def match(self, data, pt_idx):
        if 'THERMISTOR' in data['Signal ID']:
            return True
        else:
            return False


pt_rules = [RulePTPathFinder(),
            RulePTDCB(),
            RulePTPTLvSource(brkoutbrd_pin_assignments),
            RulePTPTLvReturn(brkoutbrd_pin_assignments),
            RulePTPTLvSense(brkoutbrd_pin_assignments),
            RulePTPTThermistor(brkoutbrd_pin_assignments),
            RulePTDefault()]


####################################
# Generate Altium list for PigTail #
####################################

# First, replace 'Signal ID' to DCB side definitions.
for pt_id in range(0, len(pt_descr)):
    for pt_entry in pt_descr[pt_id]:
        if pt_entry['DCB slot'] is not None:
            dcb_id = RulePD.DCBID(pt_entry['DCB slot'])
            for dcb_entry in dcb_descr[int(dcb_id)]:
                if pt_entry['SEAM pin'] == dcb_entry['SEAM pin'] \
                        and \
                        pt_entry['Pigtail pin'] == dcb_entry['Pigtail pin']:
                    pt_entry['Signal ID'] = dcb_entry['Signal ID']
                    break


# Now apply all rules defined in the previous section
PtSelector = SelectorPD(pt_descr, pt_rules)
print('====WARNINGS for PigTAIL====')
pt_result = PtSelector.do()

# Finally, write to csv file
write_to_csv(pt_result_output_filename, pt_result)
