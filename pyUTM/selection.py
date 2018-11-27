#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Nov 27, 2018 at 03:42 PM -0500

import re
import abc

from collections import defaultdict
from typing import Union, List

from pyUTM.datatype import NetNode


########################
# Abstract definitions #
########################

class Rule(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def filter(self, *args):
        '''
        General wrapper to call self.match and pass-thru related arguments.
        '''

    @abc.abstractmethod
    def match(self, *args) -> bool:
        '''
        Test if data matches this rule. Must return a Boolean.
        '''

    @abc.abstractmethod
    def process(self, *args):
        '''
        Manipulate data in a certain way if it matches the rule.
        '''

    @staticmethod
    def AND(l: list) -> bool:
        if False in l:
            return False
        else:
            return True

    @staticmethod
    def OR(l: list) -> bool:
        if True in l:
            return True
        else:
            return False


class Loop(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def loop(self,
             dataset: Union[list, dict],
             rules: List[Rule]) -> Union[list, dict]:
        '''
        Implement loop logic.
        '''


class Selector(metaclass=abc.ABCMeta):
    def __init__(self,
                 dataset: Union[list, dict],
                 loop_rules: List[List[Rule]],
                 loop_implementations: List[Loop]) -> None:
        if len(loop_rules) != len(loop_implementations):
            raise ValueError(
                "number of loop rules: {} doesn't match number of loop loop implementations {}".format(
                    len(loop_rules), len(loop_implementations)
                )
            )
        else:
            self.dataset = dataset

            # We do allow nested loops
            self.loop_rules = loop_rules
            self.loop_implementations = loop_implementations

    def do(self) -> Union[list, dict]:
        '''
        Loop through all loops.
        '''
        for rules, implementation in zip(self.loop_rules,
                                         self.loop_implementations):
            self.dataset = implementation.loop(self.dataset, rules)
        return self.dataset


###################################
# Selection rules for PigTail/DCB #
###################################

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


class LoopPD(Loop):
    def loop(self, dataset, rules):
        processed_dataset = {}

        for connector_idx in range(0, len(dataset)):
            for entry in dataset[connector_idx]:
                for rule in rules:
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


class SelectorPD(Selector):
    def __init__(self, dataset: Union[list, dict], rules: List[Rule]) -> None:
        super().__init__(dataset,
                         loop_rules=[rules],
                         loop_implementations=[LoopPD()])


##########################################
# Selection rules for schematic checking #
##########################################

class RuleNet(Rule):
    def __init__(self, node_dict, node_list, reference):
        self.node_dict = node_dict
        self.node_list = node_list
        self.reference = reference

    def filter(self, node):
        if self.match(node):
            return self.process(node)

    def process(self, node):
        return False

    def node_to_str(self, node):
        attrs = self.node_data_properties(node)

        s = ''
        for a in attrs:
            s += (a + ': ')
            if getattr(node, a) is not None:
                s += getattr(node, a)
            else:
                s += 'None'
            s += ', '

        return s[:-2]

    @staticmethod
    def node_data_properties(node):
        candidate = [attr for attr in dir(node) if not attr.startswith('_')]
        return [attr for attr in candidate if attr not in ['count', 'index']]


class LoopNet(Loop):
    def loop(self, dataset, rules):
        processed_dataset = defaultdict(list)

        for node in dataset.keys():
            for rule in rules:
                result = rule.filter(node)
                if result is False:
                    break

                elif result is not None:
                    section, entry = result
                    processed_dataset[section].append(entry)
                    break

        return processed_dataset


class SelectorNet(Selector):
    def __init__(self, dataset: Union[list, dict], rules: List[Rule]) -> None:
        super().__init__(dataset,
                         loop_rules=[rules],
                         loop_implementations=[LoopNet()])
