#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Oct 03, 2018 at 12:02 PM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.legacy import PADDING, DEPADDING


class Padder(unittest.TestCase):
    def test_padding(self):
        self.assertEqual(PADDING('A1'), 'A01')
        self.assertEqual(PADDING('A11'), 'A11')

    def test_depadding(self):
        self.assertEqual(DEPADDING('A01'), 'A1')
        self.assertEqual(DEPADDING('A11'), 'A11')


if __name__ == '__main__':
    unittest.main()
