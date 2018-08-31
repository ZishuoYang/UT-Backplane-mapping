#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri Aug 31, 2018 at 12:19 PM -0400

import re
import abc

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
                        args, attr = result
                        key = NetNode(**args)
                        processed_dataset[key] = attr
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
        dcb_idx, _, _ = s.split()
        return str(int(dcb_idx))

    @staticmethod
    def PTID(s):
        if '|' in s:
            return s
        else:
            pt_idx, _, _ = s.split()
        return str(int(pt_idx))
