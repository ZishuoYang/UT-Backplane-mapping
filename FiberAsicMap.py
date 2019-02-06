#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Feb 06, 2019 at 02:27 PM -0500

from pathlib import Path

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.common import unflatten
from AltiumNetlistGen import pt_descr
from AltiumNetlistGen import dcb_descr

output_dir = Path('output')
elk_mapping_output_filename = output_dir / Path('AsicToFiberMapping.csv')


###########
# Helpers #
###########

def unpack_one_elem_dict(d):
    return tuple(d.items())[0]


def make_dcb_ref(dcb_descr):
    dcb_ref = {}

    for jd, entries in dcb_descr.items():
        dcb_ref[jd] = {}
        for i in unflatten(entries, 'SEAM pin'):
            jd_pin, info = unpack_one_elem_dict(i)
            dcb_ref[jd][jd_pin] = info

    return dcb_ref


def filter_by_signal_id(keywords):
    def filter_functor(entry):
        matched = False

        for kw in keywords:
            if kw in entry['Signal ID']:
                matched = True
                break

        return matched
    return filter_functor


def find_matching_entries(pt_descr, dcb_ref, functor):
    result = []

    for jp, entries in pt_descr.items():
        for i in filter(functor, entries):
            try:
                jd, jd_pin = (i['DCB slot'], i['SEAM pin'])

                if i['Note'] != 'Unused':
                    i['DCB signal ID'] = dcb_ref[jd][jd_pin]['Signal ID']
                    result.append(i)

            except Exception as e:
                print('{} occured while processing DCB connector {}, pin {}'.format(
                    e.__class__.__name__, jd, jd_pin))
                print('The Pigtail side Signal ID is: {}'.format(
                    i['Signal ID']))
                break

    return result


##############################
# Unflatten DCB descriptions #
##############################
# We do this so that DCB entries can be access via entries['JDX']['PINXX']

dcb_ref_proto = make_dcb_ref(dcb_descr)


###########################
# Find ASIC elink entries #
###########################

filter_elk = filter_by_signal_id(['ASIC'])
elks_proto = find_matching_entries(pt_descr, dcb_ref_proto, filter_elk)


############################################################
# Generate ASIC elink fiber mapping for a single backplane #
############################################################
# NOTE: Here we'll use the flex type as part of the unique identifier for ASICs
#       because signal type moves with flex type (e.g. 'X-0-M'), not pigtail
#       connector label.


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

# # Initialize the dict to store fiber-asic map
# fiber_asic_descr = {}

# # Loop over the gbtx_descr list
# for dcb_idx in range(0, len(gbtx_descr)):
    # for elk in gbtx_descr[dcb_idx]:
        # if elk['PT Attr'] is not None and \
           # elk['PT Signal ID'][-1:] == 'P':
            # flex = elk['Pigtail slot'][-5:]
            # hybrid, _, asic_idx, asic_ch, _ = elk['PT Signal ID'].split('_')
            # gbtx_idx, _, gbtx_ch, _ = elk['Signal ID'].split('_')
            # is_inner, is_middle, is_outer = True, True, True

            # if elk['PT Attr'] == 'DEPOPULATED':
                # # Depopulated signals not on Middle/Outer
                # is_middle = False
                # is_outer = False
            # else:
                # # UTa-Outer does not have 8/9/10/11 (Stave-2)
                # if int(elk['Pigtail slot'][:2]) >= 8:
                    # is_outer = False

            # # 8-ASIC is seperated into WEST/EAST
            # if hybrid in ['P1', 'P2']:
                # if int(asic_idx) <= 3:
                    # asic_bp_id = flex + '_' + hybrid + 'WEST' + '_ASIC_' + asic_idx
                # else:
                    # asic_bp_id = flex + '_' + hybrid + 'EAST' + '_ASIC_' + asic_idx
            # else:
                    # asic_bp_id = flex + '_' + hybrid + '_ASIC_' + asic_idx

            # if asic_bp_id not in fiber_asic_descr.keys():
                # fiber_asic_descr[asic_bp_id] = {
                    # 'flex': flex,
                    # 'hybrid': hybrid,
                    # 'asic_idx': asic_idx,
                    # 'channels': {
                        # int(asic_ch[2:]): {
                            # 'dcb_idx': dcb_idx,
                            # 'gbtx_idx': int(gbtx_idx[2:]),
                            # 'gbtx_ch': int(gbtx_ch[2:]),
                            # 'is_inner': is_inner,
                            # 'is_middle': is_middle,
                            # 'is_outer': is_outer
                            # }
                        # }
                                                # }
            # else:
                # fiber_asic_descr[asic_bp_id]['channels'][int(asic_ch[2:])] = {
                        # 'dcb_idx': dcb_idx,
                        # 'gbtx_idx': int(gbtx_idx[2:]),
                        # 'gbtx_ch': int(gbtx_ch[2:]),
                        # 'is_inner': is_inner,
                        # 'is_middle': is_middle,
                        # 'is_outer': is_outer
                        # }

# # Check that dcb_idx and gbtx_idx do not change for single ASIC
# for i in fiber_asic_descr:
    # channel_dict = fiber_asic_descr[i]['channels']
    # keys = list(channel_dict.keys())
    # dcb = channel_dict[keys[0]]['dcb_idx']
    # for ii in keys:
        # if channel_dict[ii]['dcb_idx'] != dcb:
            # print('ERROR: more than 1 dcb_idx', i)

# for i in fiber_asic_descr:
    # channel_dict = fiber_asic_descr[i]['channels']
    # keys = list(channel_dict.keys())
    # dcb = channel_dict[keys[0]]['gbtx_idx']
    # for ii in keys:
        # if channel_dict[ii]['gbtx_idx'] != dcb:
            # print('ERROR: more than 1 gbtx_idx', i)
# # End of check


# # Now extend to 1 PEPI system (alpha+beta+gamma backplanes)


# def get_dcb_info(asic, is_inner=False, is_middle=False, is_outer=False):
    # chan_keys = list(asic['channels'].keys())
    # dcb_idx = asic['channels'][chan_keys[0]]['dcb_idx']
    # gbtx_idx = asic['channels'][chan_keys[0]]['gbtx_idx']
    # gbtx_ch = []
    # for i in chan_keys:
        # if (asic['channels'][i]['is_inner'] and is_inner) or \
                # (asic['channels'][i]['is_middle'] and is_middle) or \
                # (asic['channels'][i]['is_outer'] and is_outer):
                    # gbtx_ch.append(asic['channels'][i]['gbtx_ch'])
    # gbtx_ch.sort(reverse=True)
    # return dcb_idx, gbtx_idx, gbtx_ch


# # For all PEPI's:
# all_PEPIs = {
    # # For true-type PEPIs
    # 'Magnet-Top-C': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # ]
    # ,
    # 'Magnet-Bottom-A': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 't'},
        # ]
    # ,
    # 'IP-Top-A': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # ]
    # ,
    # 'IP-Bottom-C': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 't'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 't'}
        # ]
    # ,
    # # Now for mirror-tye PEPIs
    # 'Magnet-Bottom-C': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9C', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # ]
    # ,
    # 'Magnet-Top-A': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTbX_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTbV_7A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTbX_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTbV_8A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTbX_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTbV_9A', 'bp_var': 'middle', 'bp_abg': 'g', 'bp_type': 'm'},
        # ]
    # ,
    # 'IP-Bottom-A': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3A', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6A', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9A', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # ]
    # ,
    # 'IP-Top-C': [
        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_1C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_2C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_3C', 'bp_var': 'inner', 'bp_abg': 'a', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_4C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_5C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_6C', 'bp_var': 'middle', 'bp_abg': 'b', 'bp_type': 'm'},

        # {'stv_bp': 'X-0', 'stv_ut': 'UTaX_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-0', 'stv_ut': 'UTaU_7C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-1', 'stv_ut': 'UTaX_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-1', 'stv_ut': 'UTaU_8C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'X-2', 'stv_ut': 'UTaX_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'},
        # {'stv_bp': 'S-2', 'stv_ut': 'UTaU_9C', 'bp_var': 'outer', 'bp_abg': 'g', 'bp_type': 'm'}
        # ]
    # }

# ########################################
# # Generate list of ASICs for all PEPIs #
# ########################################

# asic_bp_id_list = sorted(fiber_asic_descr)

# # Write to CSV file
# with open('asic_map.csv', 'w') as f:
    # # Header here
    # f.write('PEPI,Stave,Flex,Hybrid,ASIC_index,BP_index(alpha/beta/gamma),' +
            # 'BP_type(true/mirrored),' + 'DCB_index,GBTx_index,' +
            # 'GBTx_channels(GBT frame bytes)' + '\n')
    # # Loop over all ASICs
    # for pepi in all_PEPIs:
        # for stave in all_PEPIs[pepi]:
            # is_inner, is_middle, is_outer = (stave['bp_var'] == 'inner'), \
                                            # (stave['bp_var'] == 'middle'), \
                                            # (stave['bp_var'] == 'outer')
            # for asic_bp_id in asic_bp_id_list:
                # if stave['stv_bp'] in asic_bp_id:
                    # asic = fiber_asic_descr[asic_bp_id]
                    # dcb_idx, gbtx_idx, gbtx_ch = get_dcb_info(asic, is_inner, is_middle, is_outer)
                    # if len(gbtx_ch) == 0: continue
                    # f.write(pepi + ',' +
                            # stave['stv_ut'] + ',' +
                            # asic['flex'] + ',' +
                            # asic['hybrid'] + ',' +
                            # asic['asic_idx'] + ',' +
                            # stave['bp_abg'] + ',' +
                            # stave['bp_type'] + ',' +
                            # str(dcb_idx) + ',' +
                            # str(gbtx_idx) + ',' +
                            # '-'.join(list(map(str, gbtx_ch))) + '\n'
                            # )
