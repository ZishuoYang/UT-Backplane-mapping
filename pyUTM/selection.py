#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Sep 18, 2018 at 05:46 PM -0400

import re
import abc

from collections import defaultdict

from pyUTM.datatype import NetNode


########################
# Abstract definitions #
########################

class Selector(metaclass=abc.ABCMeta):
    def __init__(self, full_dataset, rules):
        self.full_dataset = full_dataset
        # Note: the ORDER of the rules matters!
        self.rules = rules

    @abc.abstractmethod
    def do(self):
        '''
        Loop through self.full_dataset by rules. Break out of the loop if a rule
        is matched.
        '''


class Rule(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def filter(self, *args):
        '''
        General wrapper to call self.match and pass-thru related arguments.
        '''

    @abc.abstractmethod
    def match(self, *args):
        '''
        Test if data matches this rule. Must return a Boolean.
        '''

    @abc.abstractmethod
    def process(self, *args):
        '''
        Manipulate data in a certain way if it matches the rule.
        '''

    @staticmethod
    def AND(l):
        if False in l:
            return False
        else:
            return True

    @staticmethod
    def OR(l):
        if True in l:
            return True
        else:
            return False


###################################
# Selection rules for PigTail/DCB #
###################################

class SelectorPD(Selector):
    def do(self):
        processed_dataset = {}

        for connector_idx in range(0, len(self.full_dataset)):
            for entry in self.full_dataset[connector_idx]:
                for rule in self.rules:
                    result = rule.filter((entry, connector_idx))
                    if result is not None:
                        node_spec, prop = result

                        # Generate a 'NetNode' if 'node_spec' is a dictionary,
                        # otherwise use it as-is as a dictionary key, assume it
                        # is hashable.
                        if isinstance(node_spec, dict):
                            key = NetNode(**node_spec)
                        else:
                            key = node_spec

                        # NOTE: The insertion-order is preserved starting in
                        # Python 3.7.0.
                        processed_dataset[key] = prop
                        break

        return processed_dataset


class RulePD(Rule):
    PT_PREFIX = 'JP'
    DCB_PREFIX = 'JD'

    def filter(self, databundle):
        data, connector_idx = databundle
        if self.match(data, connector_idx):
            return self.process(data, connector_idx)

    @staticmethod
    def PADDING(s):
        # FIXME: Still unclear on how to deal with multiple pins.
        if '|' in s or '/' in s:
            # For now, return multiple pins spec as it-is.
            return s
        else:
            letter, num = filter(None, re.split(r'(\d+)', s))
            num = '0'+num if len(num) == 1 else num
            return letter+num

    @staticmethod
    def DEPADDING(s):
        if '|' in s or '/' in s:
            return s
        else:
            letter, num = filter(None, re.split(r'(\d+)', s))
            return letter + str(int(num))

    @staticmethod
    def DCBID(s):
        dcb_idx, _, _ = s.split(' ', 2)
        return str(int(dcb_idx))

    @staticmethod
    def PTID(s):
        if '|' in s:
            return s
        else:
            pt_idx, _, _ = s.split()
        return str(int(pt_idx))


##########################################
# Selection rules for schematic checking #
##########################################

class SelectorNet(Selector):
    def do(self):
        processed_dataset = defaultdict(list)

        for node in self.full_dataset.keys():
            for rule in self.rules:
                result = rule.filter(node)
                if result is not None:
                    section, entry = result
                    processed_dataset[section].append(entry)

        return processed_dataset


class RuleNet(Rule):
    def __init__(self, netlist_node_dict, reference):
        self.netlist_node_dict = netlist_node_dict
        self.netlist_node_dict_keys_list = netlist_node_dict.keys()
        self.reference = reference

    def filter(self, node):
        if self.match(node):
            return self.process(node)

    def process(self, node):
        pass

    def node_to_str(self, node):
        attrs = self.node_data_properties(node)

        s = ''
        for a in attrs:
            s += (a + ': ')
            if getattr(node, a) is not None:
                s += getattr(node, a)
            else:
                s += 'None'
            s += ','

        return s[:-1]

    @staticmethod
    def node_data_properties(node):
        candidate = [attr for attr in dir(node) if not attr.startswith('_')]
        return [attr for attr in candidate if attr not in ['count', 'index']]
