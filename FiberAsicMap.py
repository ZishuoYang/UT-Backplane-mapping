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

#  PT slot #  | Plane/Stave/Flex
#     0       | X-0-M
#     1       | X-0-S
#     2       | S-0-S
#     3       | S-0-M
#     4       | X-1-M
#     5       | X-1-S
#     6       | S-1-S
#     7       | S-1-M
#     8       | X-2-M
#     9       | X-2-S
#     10      | S-2-S
#     11      | S-2-M
#
# X/S for vertical/stereo;
# 0/1/2 for Stave index;
# M/S for DataFlex Medium/Short*
# (*except for Stave-0 where S is Long)

# Initialize the dict to store fiber-asic map
fiber_asic_descr = {}

# Loop over the gbtx_descr list
for dcb_idx in range(0, len(gbtx_descr)):
    for elk in gbtx_descr[dcb_idx]:
        if elk['PT Attr'] is not None and \
           elk['PT Signal ID'][-1:] == 'P':
            flex = elk['Pigtail slot'][-5:]
            hybrid, _, asic_idx, asic_ch, _ = elk['PT Signal ID'].split('_')
            gbtx_idx, _, gbtx_ch, _ = elk['Signal ID'].split('_')
            is_inner, is_middle, is_outer = True, True, True

            if elk['PT Attr'] == 'DEPOPULATED':
                # Depopulated signals not on Middle/Outer
                is_middle = False
                is_outer = False
            else:
                # UTa-Outer does not have 8/9/10/11 (Stave-2)
                if int(elk['Pigtail slot'][:2]) >= 8:
                    is_outer = False

            # 8-ASIC is seperated into WEST/EAST
            if hybrid in ['P1', 'P2']:
                if int(asic_idx) <= 3:
                    asic_bp_id = flex + '_' + hybrid + 'WEST' + '_ASIC_' + asic_idx
                else:
                    asic_bp_id = flex + '_' + hybrid + 'EAST' + '_ASIC_' + asic_idx
            else:
                    asic_bp_id = flex + '_' + hybrid + '_ASIC_' + asic_idx

            if asic_bp_id not in fiber_asic_descr.keys():
                fiber_asic_descr[asic_bp_id] = {
                    'flex': flex,
                    'hybrid': hybrid,
                    'asic_idx': asic_idx,
                    'channels': {
                        int(asic_ch[2:]): {
                            'dcb_idx': dcb_idx,
                            'gbtx_idx': int(gbtx_idx[2:]),
                            'gbtx_ch': int(gbtx_ch[2:]),
                            'is_inner': is_inner,
                            'is_middle': is_middle,
                            'is_outer': is_outer
                            }
                        }
                                                }
            else:
                fiber_asic_descr[asic_bp_id]['channels'][int(asic_ch[2:])] = {
                        'dcb_idx': dcb_idx,
                        'gbtx_idx': int(gbtx_idx[2:]),
                        'gbtx_ch': int(gbtx_ch[2:]),
                        'is_inner': is_inner,
                        'is_middle': is_middle,
                        'is_outer': is_outer
                        }

# Check that dcb_idx and gbtx_idx do not change for single ASIC
for i in fiber_asic_descr:
    channel_dict = fiber_asic_descr[i]['channels']
    keys = list(channel_dict.keys())
    dcb = channel_dict[keys[0]]['dcb_idx']
    for ii in keys:
        if channel_dict[ii]['dcb_idx'] != dcb:
            print('ERROR: more than 1 dcb_idx', i)

for i in fiber_asic_descr:
    channel_dict = fiber_asic_descr[i]['channels']
    keys = list(channel_dict.keys())
    dcb = channel_dict[keys[0]]['gbtx_idx']
    for ii in keys:
        if channel_dict[ii]['gbtx_idx'] != dcb:
            print('ERROR: more than 1 gbtx_idx', i)
# End of check


# Now extend to 1 PEPI system (alpha+beta+gamma backplanes)


def get_dcb_info(asic, is_inner=False, is_middle=False, is_outer=False):
    chan_keys = list(asic['channels'].keys())
    dcb_idx = asic['channels'][chan_keys[0]]['dcb_idx']
    gbtx_idx = asic['channels'][chan_keys[0]]['gbtx_idx']
    gbtx_ch = []
    for i in chan_keys:
        if (asic['channels'][i]['is_inner'] and is_inner) or \
                (asic['channels'][i]['is_middle'] and is_middle) or \
                (asic['channels'][i]['is_outer'] and is_outer):
                    gbtx_ch.append(asic['channels'][i]['gbtx_ch'])
    gbtx_ch.sort(reverse=True)
    return dcb_idx, gbtx_idx, gbtx_ch


# For all PEPI's:
all_PEPIs = {
    # For true-type PEPIs
    'Magnet-Top-C': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        ]
    ,
    'Magnet-Bottom-A': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        ]
    ,
    'IP-Top-A': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        ]
    ,
    'IP-Bottom-C': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'}
        ]
    ,
    # Now for mirror-tye PEPIs
    'Magnet-Bottom-C': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        ]
    ,
    'Magnet-Top-A': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        ]
    ,
    'IP-Bottom-A': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        ]
    ,
    'IP-Top-C': [
        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'}
        ]
    }

########################################
# Generate list of ASICs for all PEPIs #
########################################

asic_bp_id_list = sorted(fiber_asic_descr)

# Write to CSV file
with open('asic_map.csv', 'w') as f:
    # Header here
    f.write('PEPI,Stave,Flex,Hybrid,ASIC_index,BP_index(alpha/beta/gamma),' +
            'BP_type(true/mirrored),' + 'DCB_index,GBTx_index,' +
            'GBTx_channels(GBT frame bytes)' + '\n')
    # Loop over all ASICs
    for pepi in all_PEPIs:
        for stave in all_PEPIs[pepi]:
            is_inner, is_middle, is_outer = (stave['bp_var'] == 'inner'), \
                                            (stave['bp_var'] == 'middle'), \
                                            (stave['bp_var'] == 'outer')
            for asic_bp_id in asic_bp_id_list:
                if stave['stv_bp'] in asic_bp_id:
                    asic = fiber_asic_descr[asic_bp_id]
                    dcb_idx, gbtx_idx, gbtx_ch = get_dcb_info(asic, is_inner, is_middle, is_outer)
                    if len(gbtx_ch) == 0: continue
                    f.write(pepi + ',' +
                            stave['stv_ut'] + ',' +
                            asic['flex'] + ',' +
                            asic['hybrid'] + ',' +
                            asic['asic_idx'] + ',' +
                            stave['bp_abg'] + ',' +
                            stave['bp_type'] + ',' +
                            str(dcb_idx) + ',' +
                            str(gbtx_idx) + ',' +
                            '-'.join(list(map(str, gbtx_ch))) + '\n'
                            )
