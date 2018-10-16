#!/usr/bin/env python
#
# License: MIT
# Last Change: Mon Sep 24, 2018 at 01:48 PM -0400

from pathlib import Path

from pyUTM.io import XLReader, write_to_csv
from pyUTM.selection import RulePD
from pyUTM.datatype import BrkStr, GenericNetNode
from pyUTM.datatype import ExcelCell
from pyUTM.legacy import legacy_csv_line_dcb

input_dir = Path('input')
output_dir = Path('output')

pt_filename = input_dir / Path(
    'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.2.xlsm')
dcb_filename = input_dir / Path(
    'backplaneMapping_SEAMPins_trueType_v5.2.xlsm')

pt_result_output_filename = output_dir / Path('AltiumNetlist_PT.csv')
dcb_result_output_filename = output_dir / Path('AltiumNetlist_DCB.csv')


##########################
# Read info from PigTail #
##########################

PtReader = XLReader(pt_filename)
pt_descr = PtReader.read(range(0, 12), 'B5:K405',
                         sortby=lambda d: d['Signal ID'])


######################
# Read info from DCB #
######################

DcbReader = XLReader(dcb_filename)
dcb_descr = DcbReader.read(range(0, 12), 'B5:K405',
                           sortby=lambda d: d['Signal ID'])


#############################################
# Form list of data/control channels to map #
#############################################

# ASIC list from PT
asic_descr = []
for pt_idx in range(0, len(pt_descr)):
    single_pt = []
    for i in pt_descr[pt_idx]:
        if 'ASIC' in i['Signal ID']:
            if i['Signal ID'].font_color is not None and \
                    i['Signal ID'].font_color.rgb == 'FF3366FF':
                        i['Attr'] = 'DEPOPULATED'
            elif i['Signal ID'].font_color is not None and \
                    i['Signal ID'].font_color.tint != 0.0:
                        i['Attr'] = 'INVALID'
            else:
                i['Attr'] = 'REGULAR'
            single_pt.append(i)
    asic_descr.append(single_pt)


def get_pt_ch(list_descr, pt_idx, pt_pin):
    for i in list_descr[pt_idx]:
        if pt_pin == str(i['Pigtail pin']):
            return i
    print('ERROR: pt_pin not found')


# GBTx-ASIC list from DCB
gbtx_descr = []
for dcb_idx in range(0, len(dcb_descr)):
    single_dcb = []
    for i in dcb_descr[dcb_idx]:
        if '_ELK_CH' in i['Signal ID']:
            # Find GBTx-ASIC connections
            if i['Pigtail pin'] is not None:
                pt_idx = int(i['Pigtail slot'][:2])
                pt_pin = str(i['Pigtail pin'])
                asic_ch = get_pt_ch(asic_descr, pt_idx, pt_pin)
                i['PT Signal ID'] = asic_ch['Signal ID']
                i['PT Attr'] = asic_ch['Attr']
            else:
                i['PT Signal ID'] = None
                i['PT Attr'] = None
            single_dcb.append(i)
    gbtx_descr.append(single_dcb)

# Control channels on PT
control_pt_descr = []
for pt_idx in range(0, len(pt_descr)):
    single_pt = []
    for i in pt_descr[pt_idx]:
        # Get active control signals
        if i['SEAM pin'] is not None and \
                ('_CLK_' in i['Signal ID'] or
                 '_I2C_' in i['Signal ID'] or
                 '_RESET_' in i['Signal ID'] or
                 '_TFC_' in i['Signal ID']):
            if i['Signal ID'].font_color is not None and \
                    i['Signal ID'].font_color.rgb == 'FF3366FF':
                        i['Attr'] = 'DEPOPULATED'
            elif i['Signal ID'].font_color is not None and \
                    i['Signal ID'].font_color.tint != 0.0:
                        i['Attr'] = 'INVALID'
            else:
                i['Attr'] = 'REGULAR'
            single_pt.append(i)
    control_pt_descr.append(single_pt)


# Control channels on DCB
control_dcb_descr = []
for dcb_idx in range(0, len(dcb_descr)):
    single_dcb = []
    for i in dcb_descr[dcb_idx]:
        # Get control channels
        if 'DC_OUT_RCLK' in i['Signal ID'] or \
           'EC_HYB_i2C' in i['Signal ID'] or \
           'EC_RESET_GPIO' in i['Signal ID'] or \
           'MC_TFC' in i['Signal ID']:
            # Find PT - DCB connections if any
            if i['Pigtail pin'] is not None:
                pt_idx = int(i['Pigtail slot'][:2])
                pt_pin = str(i['Pigtail pin'])
                asic_ch = get_pt_ch(control_pt_descr, pt_idx, pt_pin)
                i['PT Signal ID'] = asic_ch['Signal ID']
                i['PT Attr'] = asic_ch['Attr']
            else:
                i['PT Signal ID'] = None
                i['PT Attr'] = None
            single_dcb.append(i)
    control_dcb_descr.append(single_dcb)


#################################################
# Do ASIC-Fiber mapping and control-DCB mapping #
#################################################

# Table: PT slot #  | Plane/Stave/Flex
#           0       | X-0-M
#           1       | X-0-S
#           2       | S-0-S
#           3       | S-0-M
#           4       | X-1-M
#           5       | X-1-S
#           6       | S-1-S
#           7       | S-1-M
#           8       | X-2-M
#           9       | X-2-S
#           10      | S-2-S
#           11      | S-2-M
#
# X/S for vertical/stereo;
# 0/1/2 for Stave index;
# M/S for DataFlex Medium/Short* (*except for Stave-0 where S is Long)






















