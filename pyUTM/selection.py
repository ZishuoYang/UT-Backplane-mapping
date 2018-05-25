#!/usr/bin/env python
#
# License: GPLv2
# Last Change: Fri May 25, 2018 at 04:29 AM -0400


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


###############################
# Selection rules for PigTail #
###############################


class SelectorPT(Selector):
    def do(self):
        processed_dataset = []

        for pt_connector_idx in range(0, len(self.full_dataset)):
            for entry in self.full_dataset[pt_connector_idx]:
                for rule in self.rules:
                    result = rule.filter((entry, pt_connector_idx))
                    if result is not None:
                        processed_dataset.append(result)
                        break

        return processed_dataset
