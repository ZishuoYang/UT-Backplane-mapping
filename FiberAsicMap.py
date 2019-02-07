#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Feb 07, 2019 at 09:48 AM -0500

import re

from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.common import unflatten
from pyUTM.common import jp_flex_type_proto
from AltiumNetlistGen import pt_descr
from AltiumNetlistGen import dcb_descr

output_dir = Path('output')
elk_mapping_output_filename = output_dir / Path('AsicToFiberMapping.csv')


###########
# Helpers #
###########

# Regularize input #############################################################

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


def flatten_descr(descr, header='Pigtail slot'):
    flattened = []

    for key, items in descr.items():
        for i in items:
            i[header] = key
            flattened.append(i)

    return flattened


# Make selections ##############################################################

def filter_by_signal_id(keywords):
    def filter_functor(entry):
        matched = False

        for kw in keywords:
            if bool(re.search(kw, entry['Signal ID'])):
                matched = True
                break

        return matched
    return filter_functor


def find_matching_entries(flattened, ref, functor):
    result = []

    for i in filter(functor, flattened):
        try:
            jd, jd_pin = (i['DCB slot'], i['SEAM pin'])

            if i['Note'] != 'Unused':
                i['DCB signal ID'] = ref[jd][jd_pin]['Signal ID']
                result.append(i)

        except Exception as e:
            print('{} occured while processing DCB connector {}, pin {}'.format(
                e.__class__.__name__, jd, jd_pin))
            print('The Pigtail side Signal ID is: {}'.format(
                i['Signal ID']))
            break

    return result


# Find ASIC/elink channels/etc. info ###########################################

def find_proto_flex_type(d):
    jp = d['Pigtail slot']
    return jp_flex_type_proto[jp]


def find_hybrid_asic_info(d):
    pt_signal_id = d['Signal ID']
    hybrid, _, asic_idx, asic_ch, _ = pt_signal_id.split('_')
    asic_idx = int(asic_idx)
    asic_ch = int(asic_ch[2:])
    return (hybrid, asic_idx, asic_ch)


def find_gbtx_info(d):
    dcb_signal_id = d['DCB signal ID']
    gbtx_idx, _, gbtx_ch, _ = dcb_signal_id.split('_')
    gbtx_idx = int(gbtx_idx[2:])
    gbtx_ch = int(gbtx_ch[2:])
    return (gbtx_idx, gbtx_ch)


# NOTE: asic_bp_id is used for sorting
def find_asic_bp_id(hybrid, asic_idx, flex):
    if hybrid == 'P1' or hybrid == 'P2':
        if asic_idx <= 3:
            asic_bp_id = flex + '_' + hybrid + '_WEST' + '_ASIC_' + \
                str(asic_idx)
        else:
            asic_bp_id = flex + '_' + hybrid + '_EAST' + '_ASIC_' + \
                str(asic_idx)

    else:
        asic_bp_id = flex + '_' + hybrid + '_ASIC_' + str(asic_idx)

    return asic_bp_id


def find_pt_slot(d):
    return int(d['Pigtail slot'][2:])


# Sorting ######################################################################


# Swapping JD/JP connectors for true/mirror type from backplane proto ##########


##########################
# Prepare for selections #
##########################

# Convert DCB description to a dictionary: We do this so that DCB entries can be
# access via entries['JDX']['PINXX']
dcb_ref_proto = make_dcb_ref(dcb_descr)

pt_descr_flattend = flatten_descr(pt_descr)


###########################
# Find ASIC elink entries #
###########################

filter_elk = filter_by_signal_id([r'ASIC'])
elks_proto = find_matching_entries(pt_descr_flattend, dcb_ref_proto, filter_elk)

# Now since elinks are differential signals, we have two redundant descriptions:
# one by all positive channels, one by negative channels. Here we pick positive
# channels only (fix a gauge).
filter_positive = filter_by_signal_id([r'_P$'])
elks_proto_p = find_matching_entries(elks_proto, dcb_ref_proto, filter_positive)


############################################################
# Generate ASIC elink fiber mapping for a single backplane #
############################################################
# NOTE: Here we'll use the flex type as part of the unique identifier for ASICs
#       because signal type moves with flex type (e.g. 'X-0-M'), not pigtail
#       connector label.

# Initialize elink mapppings
elks_descr_alpha = defaultdict(list)
elks_descr_beta = defaultdict(list)
elks_descr_gamma = defaultdict(list)

for elk in elks_proto_p:
    # Find flex type, this is used for all backplanes
    flex = find_proto_flex_type(elk)

    hybrid, asic_idx, asic_ch = find_hybrid_asic_info(elk)
    gbtx_idx, gbtx_ch = find_gbtx_info(elk)

    # 8-ASIC is seperated into WEST/EAST for sorting
    asic_bp_id = find_asic_bp_id(hybrid, asic_idx, flex)

    # Unconditionally append to alpha type backplane
    elks_descr_alpha[flex].append({
        'hybrid': hybrid,
        'asic_bp_id': asic_bp_id,
        'asic_idx': asic_idx,
        'asic_ch': asic_ch,
        'gbtx_ch': gbtx_ch
    })

    # Now depopulate to beta type
    if elk['Note'] != 'Alpha only':
        elks_descr_beta[flex].append({
            'hybrid': hybrid,
            'asic_bp_id': asic_bp_id,
            'asic_idx': asic_idx,
            'asic_ch': asic_ch,
            'gbtx_ch': gbtx_ch
        })

        # Finally, depopulate further to gamma
        if find_pt_slot(elk) < 8:
            elks_descr_gamma[flex].append({
                'hybrid': hybrid,
                'asic_bp_id': asic_bp_id,
                'asic_idx': asic_idx,
                'asic_ch': asic_ch,
                'gbtx_ch': gbtx_ch
            })

# Sort all elink descriptions by asic_bp_id
for k in elks_descr_alpha:


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


########################################
# Generate list of ASICs for all PEPIs #
########################################

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
