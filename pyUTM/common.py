#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 06, 2018 at 12:01 PM -0500

from collections import defaultdict


#############################
# For YAML/Excel conversion #
#############################

# Take a list of dictionaries with the same dimensionality
def transpose(l):
    result = defaultdict(list)
    for d in l:
        for k in d.keys():
            result[k].append(d[k])
    return dict(result)


# NOTE: This functions modify the 'l' in-place.
def flatten(l, header='PlaceHolder'):
    result = []
    for d in l:
        key, value = tuple(d.items())[0]
        value[header] = key
        result.append(value)
    return result


# NOTE: This functions modify the 'l' in-place.
def unflatten(l, header):
    result = []
    for d in l:
        key = d[header]
        del d[header]
        result.append({key: d})
    return result


def collect_terms(d, filter_function):
    return {k: d[k] for k in filter_function(d)}
