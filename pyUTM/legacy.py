#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Oct 09, 2018 at 12:04 PM -0400

import re

from copy import deepcopy

from pyUTM.datatype import NetNode
from pyUTM.selection import RulePD

##############
# Formatters #
##############

def legacy_csv_line_dcb(node, prop):
    s = ''
    netname = prop['NETNAME']
    attr = prop['ATTR']

    if netname is None:
        s += attr

    elif netname.endswith('1V5_M') or netname.endswith('1V5_S'):
        netname = netname[:-2]
        s += netname

    elif '2V5' in netname:
        s += netname

    elif attr is None and 'JP' not in netname:
        if netname.count('JD') > 1:
            # We are in DCB-DCB case.
            # NOTE: Now 'node' is a 'GenericNetNode', not a 'NetNode'.
            net_dcb1, net_dcb2, net_tail = netname.split('_', 2)

            if node.Node1 == net_dcb1:
                net_dcb1 += RulePD.PADDING(node.Node1_PIN)
                net_dcb2 += RulePD.PADDING(node.Node2_PIN)

            else:
                net_dcb1 += RulePD.PADDING(node.Node2_PIN)
                net_dcb2 += RulePD.PADDING(node.Node1_PIN)

            if int(node.Node1[2:]) > int(node.Node2[2:]):
                s += (net_dcb2 + '_' + net_dcb1 + '_' + net_tail)
            else:
                s += (net_dcb1 + '_' + net_dcb2 + '_' + net_tail)

            # NOTE: We also know in this case, 'Node' is a 'GenericNetNode', so
            # we convert it to a 'NetNode'.
            node = NetNode(node.Node1, node.Node1_PIN,
                           node.Node2, node.Node2_PIN)

        else:
            s += netname

    else:
        attr = '_' if attr is None else attr

        try:
            net_head, net_body, net_tail = netname.split('_', 2)

            if node.DCB is not None:
                if node.DCB in net_head:
                    net_head += RulePD.PADDING(node.DCB_PIN)

                if node.DCB in net_body:
                    net_body += RulePD.PADDING(node.DCB_PIN)

            if node.PT is not None:
                if node.PT in net_head:
                    net_head += RulePD.PADDING(node.PT_PIN)

                if node.PT in net_body:
                    net_body += RulePD.PADDING(node.PT_PIN)

            s += (net_head + attr + net_body + '_' + net_tail)

        except Exception:
            net_head, net_tail = netname.split('_', 1)

            # Take advantage of lazy Boolean evaluation in Python.
            if node.DCB is not None and node.DCB in net_head:
                net_head += RulePD.PADDING(node.DCB_PIN)

            if node.PT is not None and node.PT in net_head:
                net_head += RulePD.PADDING(node.PT_PIN)

            s += (net_head + attr + net_tail)
    s += ','

    s += node.DCB[2:] if node.DCB is not None else ''
    s += ','

    s += RulePD.PADDING(node.DCB_PIN) if node.DCB_PIN is not None else ''
    s += ','

    if node.PT is not None and '|' in node.PT:
        s += node.PT
    else:
        s += node.PT[2:] if node.PT is not None else ''
    s += ','

    s += RulePD.PADDING(node.PT_PIN) if node.PT_PIN is not None else ''

    return s


def legacy_csv_line_pt(node, prop):
    s = ''
    netname = prop['NETNAME']
    attr = prop['ATTR']

    if netname is None:
        s += attr

    elif attr is None and 'JD' not in netname:
        s += netname

    else:
        attr = '_' if attr is None else attr

        try:
            net_head, net_body, net_tail = netname.split('_', 2)

            if node.DCB is not None:
                if node.DCB in net_head:
                    net_head += RulePD.PADDING(node.DCB_PIN)

                if node.DCB in net_body:
                    net_body += RulePD.PADDING(node.DCB_PIN)

            if node.PT is not None:
                if node.PT in net_head:
                    net_head += RulePD.PADDING(node.PT_PIN)

                if node.PT in net_body:
                    net_body += RulePD.PADDING(node.PT_PIN)

            s += (net_head + attr + net_body + '_' + net_tail)

        except Exception:
            net_head, net_tail = netname.split('_', 1)

            # Take advantage of lazy Boolean evaluation in Python.
            if node.DCB is not None and node.DCB in net_head:
                net_head += RulePD.PADDING(node.DCB_PIN)

            if node.PT is not None and node.PT in net_head:
                net_head += RulePD.PADDING(node.PT_PIN)

            s += (net_head + attr + net_tail)
    s += ','

    s += node.PT[2:] if node.PT is not None else ''
    s += ','

    s += RulePD.PADDING(node.PT_PIN) if node.PT_PIN is not None else ''
    s += ','
    s += ','

    return s


##################
# Data regulator #
##################

def PADDING(s):
    letter, num = filter(None, re.split(r'(\d+)', s))
    num = '0'+num if len(num) == 1 else num
    return letter+num


def DEPADDING(s):
    letter, num = filter(None, re.split(r'(\d+)', s))
    return letter+str(int(num))


def PINID(s, padder=DEPADDING):
    if s is None:
        return s

    if '|' in s:
        pins = s.split('|')
        for idx in range(0, len(pins)):
            if '/' in pins[idx]:
                pins[idx] = list(map(padder, pins[idx].split('/')))
            else:
                pins[idx] = padder(pins[idx])

    else:
        pins = padder(s)

    return pins


def CONID(s, prefix=lambda x: 'JP'+str(int(x))):
    if s is None:
        return s

    if '|' in s:
        connectors = list(map(prefix, s.split('|')))
    else:
        connectors, _, _  = s.split(' ', 2)
        connectors = prefix(connectors)
    return connectors


def make_entries(entries, entry, pin_id, connector_id, pins, connectors):
    if type(pins) == list and type(connectors) == list:
        for p in pins:
            for c in connectors:
                temp_entry = deepcopy(entry)
                temp_entry[pin_id] = p
                temp_entry[connector_id] = c
                entries.append(temp_entry)

    else:
        entry[pin_id] = pins
        entry[connector_id] = connectors
        entries.append(entry)
