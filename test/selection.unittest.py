#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 01:15 AM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.selection import RulePD


class RulePDTester(unittest.TestCase):
    def test_padding(self):
        self.assertEqual(RulePD.PADDING('A1'), 'A01')
        self.assertEqual(RulePD.PADDING('A11'), 'A11')


if __name__ == '__main__':
    unittest.main()
