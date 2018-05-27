#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 01:09 AM -0400

from os.path import join

from pyUTM.io import XLReader
from pyUTM.selection import SelectorPD, RulePD


############################################
# Read pin assignments from breakout board #
############################################

filename_brkoutbrd = join('templates',
                          'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')
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
                       sortby=lambda d: d['Src'],
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

filename_pt = join('templates',
                   'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')
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
    def match(self, data, connector_idx):
        # This needs to be placed at the end of the rules list.
        # It always returns 'True' to handle entries NOT matched by any other
        # rules.
        return True

    def process(self, data, connector_idx):
        print('WARNING: The following entry is not matched by any other rules!')
        print('Connector index: %s. Pigtail Pin: %s.' % (connector_idx,
                                                         data['Pigtail pin']))


class RulePTPathFinder(RulePD):
    def match(self, data, connector_idx):
        # For slot 0 or 1, we need to process the non-BOB nets so skip this
        # rule.
        if connector_idx in [0, 1]:
            return False

        # For path finder, skip non-BOB nets when not in slot 0 or 1
        keywords = ['LV_SOURCE', 'LV_RETURN', 'LV_SENSE']
        result = [False if kw in data['Signal ID'] else True for kw in keywords]
        return self.AND(result)

    def process(self, data, connector_idx):
        print('The following pin will be skipped: %s %s'
              % (connector_idx, data['PigTail pin']))


####################################
# Generate Altium list for PigTail #
####################################
