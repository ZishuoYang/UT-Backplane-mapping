#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Nov 05, 2019 at 03:12 PM -0500

import sys

from pathlib import Path
from csv import DictReader
from collections import defaultdict

output_dir = Path('output')
mapping_output_filename = output_dir / Path('AsicToFiberMapping.csv')

bp_type_mapping = {
    'true': 'Magnet-Top-C',
}


##############################
# Pigtail naming translation #
##############################

jp_true_type_aux = {
    0: ('X', 'M'),
    1: ('X', 'S'),
    2: ('S', 'S'),
    3: ('S', 'M'),
}


def jp_name_gen(idx, template):
    return '{1}-{0}-{2}'.format(idx, *template)


def jp_type_translate(jp_type_aux):
    jp_type = {}
    for jp in range(12):
        idx = jp // 4
        template =  jp_type_aux[jp % 4]
        jp_type['JP{}'.format(jp)] = jp_name_gen(idx, template)

    return jp_type


###########
# Helpers #
###########

def parse_elinks(s):
    return list(map(int, s.split('-')))


def read(file):
    with open(file, 'r') as f:
        reader = DictReader(f)
        return [dict(row) for row in reader]


def filter_on_bp_type(l, pepi_type):
    return [d for d in l if d['PEPI'] == pepi_type]


def filter_on_variant(l, variant_type):
    return [d for d in l if d['BP variant (alpha/beta/gamma)'] == variant_type]


def filter_on_jp(l, flex_type):
    return [d for d in l if d['Flex'] == flex_type]


def jd_init_dict():
    return {str(gbtx): {'i2c': None, 'elinks': list()}
            for gbtx in range(1, 7)}


def jds_per_jp(l, jp, jp_to_flex):
    result = defaultdict(jd_init_dict)
    flex_type = jp_to_flex[jp]

    for data in filter_on_jp(l, flex_type):
        jd = data['DCB index']
        gbtx = str(int(data['GBTx index'])+1)
        i2c = data['EC_HYB_I2C_SCL']
        elinks = parse_elinks(data['GBTx channels (GBT frame bytes)'])

        result[jd][gbtx]['i2c'] = i2c
        result[jd][gbtx]['elinks'] += elinks

    return result


def output_to_markdown(jp, data):
    print('- `{}`'.format(jp))
    for jd in range(12):
        for gbtx in range(1, 7):
            row = data[str(jd)][str(gbtx)]
            if row['i2c']:
                print('  - [ ] `JD{}` GBTx {} (I2C {}): {}'.format(
                    jd, gbtx, row['i2c'],
                    '-'.join(map(str, sorted(row['elinks'], reverse=True)))
                ))


##########
# Output #
##########


if __name__ == '__main__':
    bp_type, variant, jp = sys.argv[1:]
    if bp_type == 'true':
        jp_type_mapping = jp_type_translate(jp_true_type_aux)

    raw = read(mapping_output_filename)
    bp_filtered = filter_on_bp_type(raw, bp_type_mapping[bp_type])
    var_filtered = filter_on_variant(bp_filtered, variant)

    output = jds_per_jp(var_filtered, jp, jp_type_mapping)
    output_to_markdown(jp, output)
