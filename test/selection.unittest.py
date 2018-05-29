#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue May 29, 2018 at 05:19 PM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.selection import RulePD, SelectorPD


class RuleDummy(RulePD):
    TOTAL_TRUE = 0
    TOTAL_FALSE = 0

    def match(self, data, idx):
        if idx != 0:
            self.TOTAL_TRUE += 1
            return True
        else:
            self.TOTAL_FALSE += 1
            False

    def process(self, data, idx):
        return str(data)


class RulePDTester(unittest.TestCase):
    def test_padding(self):
        self.assertEqual(RulePD.PADDING('A1'), 'A01')
        self.assertEqual(RulePD.PADDING('A11'), 'A11')

    def test_dcb_id(self):
        self.assertEqual(RulePD.DCBID('00 / X-0'), '0')

    def test_pt_id(self):
        self.assertEqual(RulePD.PTID('01 / X-0-S'), '1')
        self.assertEqual(RulePD.PTID('00|01'), '00|01')


class SelectorPDTester(unittest.TestCase):
    def test_dummy_rule_populated(self):
        dataset = ((1, 2, 3, 4), ('A', 'B', 'C'))
        rule = RuleDummy()
        selector = SelectorPD(dataset, [rule])
        selector.do()
        self.assertEqual(rule.TOTAL_TRUE, 3)
        self.assertEqual(rule.TOTAL_FALSE, 4)

    def test_with_dummy(self):
        dataset = ((1, 2, 3, 4), ('A', 'B', 'C'))
        rule = RuleDummy()
        selector = SelectorPD(dataset, [rule])
        result = selector.do()
        self.assertEqual(result, ['A', 'B', 'C'])


if __name__ == '__main__':
    unittest.main()
