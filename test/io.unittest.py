#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 03:21 PM -0400

import unittest
from os.path import join

import sys
sys.path.insert(0, '..')

from utm.io import parse_cell_range, XLReader

xlsm_filename = join('..', 'templates', 'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')


class ParseCellRangeTester(unittest.TestCase):
    def test_parsing(self):
        cell_range = 'A12:CC344'
        initial_col, initial_row, final_col, final_row = parse_cell_range(
            cell_range
        )
        self.assertEqual(str(initial_col), 'A')
        self.assertEqual(initial_row, 12)
        self.assertEqual(str(final_col), 'CD')
        self.assertEqual(final_row, 345)

    def test_parsing_make_upper(self):
        cell_range = 'a12:cC344'
        initial_col, initial_row, final_col, final_row = parse_cell_range(
            cell_range
        )
        self.assertEqual(str(initial_col), 'A')
        self.assertEqual(initial_row, 12)
        self.assertEqual(str(final_col), 'CD')
        self.assertEqual(final_row, 345)


class XLReaderTester(unittest.TestCase):
    def test_read_single_spec(self):
        reader = XLReader(xlsm_filename, [0, ], 'B5:H6')
        result = reader.read()
        self.assertEqual(result[0][0]['ref'], 199)


if __name__ == '__main__':
    unittest.main()
