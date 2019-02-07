#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Feb 07, 2019 at 11:28 AM -0500

import re

from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.common import unflatten
from pyUTM.common import jp_flex_type_proto, all_pepis
from AltiumNetlistGen import pt_descr, dcb_descr

output_dir = Path('output')
elk_mapping_output_filename = output_dir / Path('AsicToElkFiberMapping.csv')
ctrl_mapping_output_filename = output_dir / Path('AsicToCtrlFiberMapping.csv')


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
            asic_bp_id = hybrid + '_WEST' + '_ASIC_' +  str(asic_idx)
        else:
            asic_bp_id = hybrid + '_EAST' + '_ASIC_' + str(asic_idx)

    else:
        asic_bp_id = hybrid + '_ASIC_' + str(asic_idx)

    return asic_bp_id


def find_slot_idx(d, key='Pigtail slot'):
    return int(d[key][2:])


# Regularize output ############################################################

def combine_asic_channels(asic_descr):
    for flex, flex_descr in asic_descr.items():
        for asic, asic_chs in flex_descr.items():
            # Error checking: Make sure ASIC elinks are connected to the same
            # GBTx on the same DCB
            dcb_ids = list(set(map(lambda x: x['dcb_idx'], asic_chs)))
            gbtx_ids = list(set(map(lambda x: x['gbtx_idx'], asic_chs)))
            if len(gbtx_ids) > 1 or len(dcb_ids) > 1:
                raise ValueError(
                    'More than one GBTx connected to {}-{}'.format(flex, asic))

            # Now combine channels
            gbtx_chs = map(lambda x: x['gbtx_ch'], asic_chs)
            asic_descr[flex][asic] = {
                'dcb_idx': dcb_ids[0],
                'gbtx_idx': gbtx_ids[0],
                'gbtx_chs':
                ','.join(map(str, sorted(gbtx_chs, reverse=True)))
            }


# Swapping JD/JP connectors for true/mirror type from backplane proto

# Output #######################################################################

def make_all_descr(descr, header=['inner', 'middle', 'outer']):
    return dict(zip(header, descr))


def generate_descr_for_all_pepi(all_descr):
    flattened_all_pepis = flatten_descr(all_pepis, header='PEPI')
    data = []

    for pepi in flattened_all_pepis:
        for flex_type in ['M', 'S']:
            pass

    return data


def write_to_csv(filename, data,
                 header={
                     'PEPI': 'PEPI',
                     'Stave': 0,
                     'Flex': 0,
                     'Hybrid': 0,
                     'ASIC index': 0,
                     'BP index (alpha/beta/gamma)': 0,
                     'BP type (true/mirrored)': 0,
                     'DCB index': 0,
                     'GBTx index': 0,
                     'GBTx channels (GBT frame bytes)': 0,
                 },
                 mode='w', eol='\n'):
    with open(filename, mode) as f:
        f.write(','.join(header.keys()) + eol)


##########################
# Prepare for selections #
##########################

# Convert DCB description to a dictionary: We do this so that DCB entries can be
# access via entries['JDX']['PINXX'].
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
elks_descr_alpha = defaultdict(lambda: defaultdict(list))
elks_descr_beta  = defaultdict(lambda: defaultdict(list))
elks_descr_gamma = defaultdict(lambda: defaultdict(list))

for elk in elks_proto_p:
    # Find flex type, this is used for all backplanes.
    flex = find_proto_flex_type(elk)

    hybrid, asic_idx, asic_ch = find_hybrid_asic_info(elk)
    gbtx_idx, gbtx_ch = find_gbtx_info(elk)

    # 8-ASIC is seperated into WEST/EAST for sorting.
    asic_bp_id = find_asic_bp_id(hybrid, asic_idx, flex)

    # Unconditionally append to alpha type backplane.
    elks_descr_alpha[flex][asic_bp_id].append({
        'hybrid': hybrid,
        'asic_idx': asic_idx,
        'asic_ch': asic_ch,
        'dcb_idx': find_slot_idx(elk, key='DCB slot'),
        'gbtx_idx': gbtx_idx,
        'gbtx_ch': gbtx_ch
    })

    # Now depopulate to beta type.
    if elk['Note'] != 'Alpha only':
        elks_descr_beta[flex][asic_bp_id].append({
            'hybrid': hybrid,
            'asic_idx': asic_idx,
            'asic_ch': asic_ch,
            'dcb_idx': find_slot_idx(elk, key='DCB slot'),
            'gbtx_idx': gbtx_idx,
            'gbtx_ch': gbtx_ch
        })

        # Finally, depopulate further to gamma.
        if find_slot_idx(elk) < 8:
            elks_descr_gamma[flex][asic_bp_id].append({
                'hybrid': hybrid,
                'asic_idx': asic_idx,
                'asic_ch': asic_ch,
                'dcb_idx': find_slot_idx(elk, key='DCB slot'),
                'gbtx_idx': gbtx_idx,
                'gbtx_ch': gbtx_ch
            })


# Combine GBTx channels for each ASIC on each flex, and check errors at the same
# time.
all_elk_descr = make_all_descr(
    [elks_descr_alpha, elks_descr_beta, elks_descr_gamma])

for _, i in all_elk_descr.items():
    combine_asic_channels(i)


#################
# Output to csv #
#################

write_to_csv(elk_mapping_output_filename, all_elk_descr)
