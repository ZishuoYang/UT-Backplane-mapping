#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 01:20 PM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.selection import RulePD


class RulePDTester(unittest.TestCase):
    def test_padding(self):
        self.assertEqual(RulePD.PADDING('A1'), 'A01')
        self.assertEqual(RulePD.PADDING('A11'), 'A11')

    def test_dcb_id(self):
        self.assertEqual(RulePD.DCBID('00 / X-0'), '0')

    def test_pt_id(self):
        self.assertEqual(RulePD.PTID('01 / X-0-S'), '1')
        self.assertEqual(RulePD.PTID('00|01'), '0')


if __name__ == '__main__':
    unittest.main()
