#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 04:22 AM -0400

from os.path import join

from pyUTM.io import XLReader
from pyUTM.selection import SelectorPD, RulePD

filename_brkoutbrd = join('templates',
                          'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')
filename_pt = join('templates',
                   'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')


############################################
# Read pin assignments from breakout board #
############################################

BrkReader = XLReader(filename_brkoutbrd)
cell_range_headers = {
    'A4:D18':    {'A': 'Src', 'D': 'Dest'},
    'F4:I18':    {'F': 'Src', 'I': 'Dest'},
    'A55:D69':   {'A': 'Src', 'D': 'Dest'},
    'F55:I69':   {'F': 'Src', 'I': 'Dest'},
    'A106:D120': {'A': 'Src', 'D': 'Dest'},
    'F106:I120': {'F': 'Src', 'I': 'Dest'},
    'K4:N53':    {'K': 'Src', 'N': 'Dest'},
    'K55:N104':  {'K': 'Src', 'N': 'Dest'},
    'K106:N155': {'K': 'Src', 'N': 'Dest'}
}

brkoutbrd_pin_assignments = list()
for cell_range in cell_range_headers.keys():
    # Note: 'extend' is used so we won't get a nested list.
    brkoutbrd_pin_assignments.extend(filter(
        # This filter is to remove entries without a source connector
        lambda d: d['Src'] is not None,
        BrkReader.read(['PinAssignments'], cell_range,
                       headers=cell_range_headers[cell_range])[0]
    ))

# We see that there's a couple of entries with both source and destination being
# 'GND'. We should remove these duplicated entries.
brkoutbrd_pin_assignments = filter(
    lambda d: d['Src'] != 'GND' or d['Dest'] != 'GND',
    brkoutbrd_pin_assignments
)


##########################
# Read info from PigTail #
##########################

PTReader = XLReader(filename_pt)
pt_descr = XLReader.read(range(0, 12), 'B5:K405',
                         sortby=lambda d: d['Pigtail pin'])


########################################
# Define rules for PigTail Altium list #
########################################
# Each of Zishuo's list entry is defined as:
#   ['DCB slot #', 'DCB connector letter pin', 'DCB connector numerical pin',
#    'PT slot #',  'PT connector letter pin',  'PT connector numerical pin',
#    'Signal ID']


class RulePTDefault(RulePD):
    def match(self, data, pt_idx):
        # This needs to be placed at the end of the rules list.
        # It always returns 'True' to handle entries NOT matched by any other
        # rules.
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
        print('WARNING: The following pin does not have a connection!: %s %s'
              % (pt_idx, data['PigTail pin']))


class RulePTDCB(RulePD):
    def match(self, data, pt_idx):
        if data['SEAM pin'] is not None:
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
    def match(self, data, pt_idx):
        if 'LV_SOURCE' in data['Signal ID']:
            return True
        else:
            return False

    def process(self, data, pt_idx):
        connection = self.PT_PREFIX + \
            str(pt_idx) + self.PADDING(data['Pigtail pin']) + \
            '_ForRefOnly_' + data['Signal ID']


pt_rules = [RulePTPathFinder(),
            RulePTDCB(),
            RulePTPTLvSource(),
            RulePTDefault()]

####################################
# Generate Altium list for PigTail #
####################################
