#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Oct 03, 2018 at 03:16 PM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.legacy import PADDING, DEPADDING
from pyUTM.legacy import PINID
from pyUTM.legacy import CONID


class PadderTester(unittest.TestCase):
    def test_padding(self):
        self.assertEqual(PADDING('A1'), 'A01')
        self.assertEqual(PADDING('A11'), 'A11')

    def test_depadding(self):
        self.assertEqual(DEPADDING('A01'), 'A1')
        self.assertEqual(DEPADDING('A11'), 'A11')


class PinIdTester(unittest.TestCase):
    def test_nominal(self):
        self.assertEqual(PINID('A11'), 'A11')

    def test_nominal_with_depadding(self):
        self.assertEqual(PINID('A01'), 'A1')

    def test_nominal_disable_depadding(self):
        self.assertEqual(PINID('A01', padder=lambda x: x), 'A01')

    def test_simple_separation(self):
        self.assertEqual(PINID('A11|B12'), ['A11', 'B12'])

    def test_simple_separation_with_depadding(self):
        self.assertEqual(PINID('A01|B02'), ['A1', 'B2'])

    def test_one_two_separation(self):
        self.assertEqual(PINID('A11|B12/B13'), ['A11', ['B12', 'B13']])

    def test_one_two_separation_with_depadding(self):
        self.assertEqual(PINID('A01|B02/B03'), ['A1', ['B2', 'B3']])

    def test_two_two_separation(self):
        self.assertEqual(PINID('A1/A2|B2/B3'), [['A1', 'A2'], ['B2', 'B3']])


class ConIdTester(unittest.TestCase):
    def test_nominal(self):
        self.assertEqual(CONID('00'), 'JP0')

    def test_multiple(self):
        self.assertEqual(CONID('00|01|02'), ['JP0', 'JP1', 'JP2'])

    def test_dcb_multiple(self):
        self.assertEqual(CONID('00|01', lambda x: 'JD'+str(int(x))),
                         ['JD0', 'JD1'])


if __name__ == '__main__':
    unittest.main()
