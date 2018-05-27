#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 03:33 AM -0400

import re


########################
# Abstract definitions #
########################
# Treat these as pseudo code.


class Selector(object):
    def __init__(self, full_dataset, rules):
        self.full_dataset = full_dataset
        # Note: the ORDER of the rules matters!
        self.rules = rules

    def do(self):
        processed_dataset = []

        for i in self.full_dataset:
            for rule in self.rules:
                result = rule.filter(i)
                if result is not None:
                    processed_dataset.append(result)
                    break

        return processed_dataset


class Rule(object):
    def filter(self, databundle):
        data = databundle
        if self.match(data):
            return data


###################################
# Selection rules for PigTail/DCB #
###################################


class SelectorPD(Selector):
    def do(self):
        processed_dataset = []

        for connector_idx in range(0, len(self.full_dataset)):
            for entry in self.full_dataset[connector_idx]:
                for rule in self.rules:
                    result = rule.filter((entry, connector_idx))
                    if result is not None:
                        processed_dataset.append(result)
                        break

        return processed_dataset


class RulePD(Rule):
    PT_PREFIX = 'JP'
    DCB_PREFIX = 'JD'

    def filter(self, databundle):
        data, connector_idx = databundle
        if self.match(data, connector_idx):
            self.process(data, connector_idx)

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
        letter, num = filter(None, re.split(r'(\d+)', s))
        num = '0'+num if len(num) == 1 else num
        return letter+num

    @staticmethod
    def DCBID(s):
        dcb_idx, _, _ = s.split()
        return str(int(dcb_idx))
