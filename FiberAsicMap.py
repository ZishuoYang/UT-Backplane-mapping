#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri Mar 01, 2019 at 05:18 PM -0500

import re

from pathlib import Path
from collections import defaultdict
from copy import deepcopy

import sys
sys.path.insert(0, './pyUTM')

from pyUTM.common import flatten_more, unflatten_all
from pyUTM.common import jp_flex_type_proto, all_pepis
from pyUTM.common import jd_swapping_true, jd_swapping_mirror
from pyUTM.io import write_to_csv
from AltiumNetlistGen import pt_descr, dcb_descr

output_dir = Path('output')
mapping_output_filename = output_dir / Path('AsicToFiberMapping.csv')


###########
# Helpers #
###########

# Filtering ####################################################################

def filter_by_signal_id(keywords):
    def filter_functor(entry):
        return True if True in [bool(re.search(kw, entry['Signal ID']))
                                for kw in keywords] else False

    return filter_functor


def find_matching_entries(flattened, ref, functor, continue_on_error=False):
    result = []

    for i in filter(functor, flattened):
        try:
            jd, jd_pin = (i['DCB slot'], i['SEAM pin'])

            if i['Note'] != 'Unused':
                i['DCB signal ID'] = ref[jd][jd_pin]['Signal ID']
                result.append(i)

        except Exception as e:
            if not continue_on_error:
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

    try:
        hybrid, _, asic_idx, asic_ch, _ = pt_signal_id.split('_')
        asic_idx = int(asic_idx)
        asic_ch = int(asic_ch[2:])
        return (hybrid, asic_idx, asic_ch)

    except Exception:
        raise ValueError("Can't parse signal ID: {}".format(pt_signal_id))


def find_gbtx_info(d):
    dcb_signal_id = d['DCB signal ID']
    gbtx_idx, _, gbtx_ch, _ = dcb_signal_id.split('_')
    gbtx_idx = int(gbtx_idx[2:])
    gbtx_ch = int(gbtx_ch[2:])
    return (gbtx_idx, gbtx_ch)


def find_hybrid_info(d):
    pt_signal_id = d['Signal ID']
    hybrid, east_west, _ = pt_signal_id.split('_', 2)
    if east_west in ['EAST', 'WEST']:
        hybrid = hybrid + '_' + east_west
    return hybrid


# NOTE: asic_bp_id is used for sorting
def gen_asic_bp_id(hybrid, asic_idx, flex):
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

def combine_asic_elk_channels(asic_descr):
    for flex, flex_descr in asic_descr.items():
        for asic, asic_chs in flex_descr.items():
            # Error checking: Make sure ASIC elinks are connected to the same
            # GBTx on the same DCB
            hybrid = list(set(map(lambda x: x['hybrid'], asic_chs)))
            asic_id = list(set(map(lambda x: x['asic_idx'], asic_chs)))
            dcb_id = list(set(map(lambda x: x['dcb_idx'], asic_chs)))
            gbtx_id = list(set(map(lambda x: x['gbtx_idx'], asic_chs)))
            if len(gbtx_id) > 1 or len(dcb_id) > 1 or len(hybrid) > 1 or \
                    len(asic_id) > 1:
                raise ValueError(
                    'More than one GBTx connected to {}-{}'.format(flex, asic))

            # Now combine channels
            gbtx_chs = map(lambda x: x['gbtx_ch'], asic_chs)
            asic_descr[flex][asic] = {
                'hybrid': hybrid[0],
                'asic_idx': asic_id[0],
                'dcb_idx': dcb_id[0],
                'gbtx_idx': gbtx_id[0],
                'gbtx_chs':
                '-'.join(map(str, sorted(gbtx_chs, reverse=True)))
            }


# Output #######################################################################

def make_all_descr(descr, header=['alpha', 'beta', 'gamma']):
    return dict(zip(header, descr))


def find_dcb_idx_based_on_bp_type(idx, bp_type):
    jd_connector = 'JD' + str(idx)

    if bp_type == 't':
        ref = jd_swapping_true
    elif bp_type == 'm':
        ref = jd_swapping_mirror
    else:
        raise ValueError('Unknown backplane type: {}'.format(bp_type))

    return ref[jd_connector][2:]


def generate_descr_for_all_pepi(all_descr):
    flattened_all_pepis = flatten_more(all_pepis, header='pepi')
    data = []

    for pepi in flattened_all_pepis:
        for flex_type_suffix in ['-M', '-S']:

            bp_variant = pepi['bp_var']
            flex_type = pepi['stv_bp'] + flex_type_suffix

            if flex_type in all_descr[bp_variant].keys():
                pointer = all_descr[bp_variant][flex_type]
                for asic_type in sorted(pointer.keys()):
                    asic_descr = pointer[asic_type]
                    entry = deepcopy(pepi)
                    entry['stv_bp'] = flex_type
                    entry['hybrid'] = asic_descr['hybrid']
                    entry['asic_idx'] = str(asic_descr['asic_idx'])

                    # Handle the only true-mirror difference here.
                    entry['dcb_idx'] = find_dcb_idx_based_on_bp_type(
                        asic_descr['dcb_idx'], pepi['bp_type']
                    )

                    entry['gbtx_idx'] = str(asic_descr['gbtx_idx'])
                    entry['gbtx_chs'] = asic_descr['gbtx_chs']
                    entry['DC_OUT_RCLK'] = asic_descr['DC_OUT_RCLK']
                    entry['MC_TFC'] = asic_descr['MC_TFC']
                    entry['EC_HYB_I2C_SCL'] = asic_descr['EC_HYB_i2C_SCL']
                    entry['EC_HYB_I2C_SDA'] = asic_descr['EC_HYB_i2C_SDA']
                    entry['EC_RESET_GPIO'] = asic_descr['EC_RESET_GPIO']

                    try:
                        entry['EC_ADC'] = asic_descr['EC_ADC']
                    except KeyError:
                        entry['EC_ADC'] = None

                    data.append(entry)

    return data


##########################
# Prepare for selections #
##########################

# Convert DCB description to a dictionary: We do this so that DCB entries can be
# access via entries['JDX']['PINXX'].
dcb_ref_proto = unflatten_all(dcb_descr, 'SEAM pin')

pt_descr_flattend = flatten_more(pt_descr, 'Pigtail slot')


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

# Initialize elink mappings
elks_descr_alpha = defaultdict(lambda: defaultdict(list))
elks_descr_beta  = defaultdict(lambda: defaultdict(list))
elks_descr_gamma = defaultdict(lambda: defaultdict(list))

for elk in elks_proto_p:
    # Find flex type, this is used for all backplanes.
    flex = find_proto_flex_type(elk)

    hybrid, asic_idx, asic_ch = find_hybrid_asic_info(elk)
    gbtx_idx, gbtx_ch = find_gbtx_info(elk)

    # 8-ASIC is seperated into WEST/EAST for sorting.
    asic_bp_id = gen_asic_bp_id(hybrid, asic_idx, flex)

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
    if elk['Note'] is None or 'Alpha only' not in elk['Note']:
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
    combine_asic_elk_channels(i)


#############################
# Find ASIC control entries #
#############################

filter_ctrl = filter_by_signal_id([r'_CLK_', r'_I2C_S', r'_RESET_', r'_TFC_',
                                   '_THERMISTOR_'])
ctrl_proto = find_matching_entries(pt_descr_flattend, dcb_ref_proto,
                                   filter_ctrl, continue_on_error=True)

# For control signals, we have to use the positive legs, because frequently,
# negative legs are connected to the ground.
ctrl_proto_p = find_matching_entries(ctrl_proto, dcb_ref_proto, filter_positive)

# Reformat some signal types
for ctrl in ctrl_proto_p:
    sig_id = ctrl['DCB signal ID']
    if 'DC_OUT_RCLK' in sig_id or 'MC_TFC' in sig_id:
        # e.g. DC_OUT_RCLK2_P
        ctrl['DCB signal ID'] = sig_id[:-3] + '_' + sig_id[-3]


##############################################################
# Generate ASIC control fiber mapping for a single backplane #
##############################################################

for ctrl in ctrl_proto_p:
    flex = find_proto_flex_type(ctrl)
    hybrid = find_hybrid_info(ctrl)
    # Alpha
    for asic_bp_id in elks_descr_alpha[flex].keys():
        if hybrid in asic_bp_id:
            signal, channel = ctrl['DCB signal ID'].rsplit('_', 1)
            elks_descr_alpha[flex][asic_bp_id][signal] = channel
    # Beta
    if ctrl['Note'] is None or 'Alpha only' not in ctrl['Note']:
        for asic_bp_id in elks_descr_beta[flex].keys():
            if hybrid in asic_bp_id:
                signal, channel = ctrl['DCB signal ID'].rsplit('_', 1)
                elks_descr_beta[flex][asic_bp_id][signal] = channel
        # Gamma
        if find_slot_idx(ctrl) < 8:
            for asic_bp_id in elks_descr_gamma[flex].keys():
                if hybrid in asic_bp_id:
                    signal, channel = ctrl['DCB signal ID'].rsplit('_', 1)
                    elks_descr_gamma[flex][asic_bp_id][signal] = channel


#################
# Output to csv #
#################

elk_data = generate_descr_for_all_pepi(all_elk_descr)

# Make sure total number of termistor 'None' channels makes sense
total_therm_none = 0
for i in elk_data:
    if i['EC_ADC'] is None:
        total_therm_none += 1
try:
    assert total_therm_none == 864
except AssertionError:
    print('Number of control links that do not go DCBs are: {}'.format(
        total_therm_none
    ))

# Unitarity tests
if len(elk_data) != 4192:
    raise ValueError(
        'Length of output data is {}, which is not 4192'.format(len(elk_data)))

# Unit tests
elif (elk_data[0]['dcb_idx'] != '2' or
      elk_data[0]['DC_OUT_RCLK'] != '5' or
      elk_data[0]['MC_TFC'] != '5' or
      elk_data[0]['EC_HYB_I2C_SCL'] != '5' or
      elk_data[0]['EC_HYB_I2C_SDA'] != '5' or
      elk_data[0]['EC_RESET_GPIO'] != '5' or
      elk_data[0]['EC_ADC'] is not None):
    raise ValueError('Unit test failed: {}'.format(elk_data[0]))
elif (elk_data[224]['dcb_idx'] != '1' or
      elk_data[224]['DC_OUT_RCLK'] != '4' or
      elk_data[224]['MC_TFC'] != '4' or
      elk_data[224]['EC_HYB_I2C_SCL'] != '4' or
      elk_data[224]['EC_HYB_I2C_SDA'] != '4' or
      elk_data[224]['EC_RESET_GPIO'] != '4' or
      elk_data[224]['EC_ADC'] != '6'):
    raise ValueError('Unit test failed: {}'.format(elk_data[224]))
elif (elk_data[3000]['dcb_idx'] != '11' or
      elk_data[3000]['DC_OUT_RCLK'] != '0' or
      elk_data[3000]['stv_bp'] != 'X-2-S' or
      elk_data[3000]['stv_ut'] != 'UTbX_6A' or
      elk_data[3000]['bp_var'] != 'beta' or
      elk_data[3000]['bp_idx'] != 'middle' or
      elk_data[3000]['bp_type'] != 'm'):
    raise ValueError('Unit test failed: {}'.format(elk_data[3000]))


# Write to csv
else:
    write_to_csv(mapping_output_filename, elk_data,
                 {'PEPI': 'pepi',
                  'Stave': 'stv_ut',
                  'Flex': 'stv_bp',
                  'Hybrid': 'hybrid',
                  'ASIC index': 'asic_idx',
                  'BP variant (alpha/beta/gamma)': 'bp_var',
                  'BP index (inner/middle/outer)': 'bp_idx',
                  'BP type (true/mirrored)': 'bp_type',
                  'DCB index': 'dcb_idx',
                  'GBTx index': 'gbtx_idx',
                  'GBTx channels (GBT frame bytes)': 'gbtx_chs',
                  'DC_OUT_RCLK': 'DC_OUT_RCLK',
                  'MC_TFC': 'MC_TFC',
                  'EC_HYB_I2C_SCL': 'EC_HYB_I2C_SCL',
                  'EC_HYB_I2C_SDA': 'EC_HYB_I2C_SDA',
                  'EC_RESET_GPIO': 'EC_RESET_GPIO',
                  'EC_ADC': 'EC_ADC'})
