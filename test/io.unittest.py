#!/usr/bin/env python
#
# License: MIT
# Last Change: Fri May 25, 2018 at 04:56 PM -0400

import unittest
from os.path import join

import sys
sys.path.insert(0, '..')

from utm.io import parse_cell_range, XLReader

pt_filename = join('..', 'templates', 'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')
brkoutbrd_filename = join('..', 'templates',
                          'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')


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
        reader = XLReader(pt_filename)
        result = reader.read([0], 'B5:H6')
        self.assertEqual(result[0][0]['ref'], 199)

    def test_read_sort(self):
        reader = XLReader(pt_filename)
        result = reader.read([0], 'B5:H11',
                             sortby=lambda item: item['SEAM pin'])
        self.assertEqual(result[0][0]['ref'], 228)
        self.assertEqual(result[0][2]['ref'], 207)
        self.assertEqual(result[0][-1]['ref'], 200)

    def test_read_with_headers_single_spec(self):
        reader = XLReader(brkoutbrd_filename)
        headers = {'A': 'Conn', 'D': 'Descr'}
        result = reader.read(['PinAssignments'], 'A4:D18', headers=headers)
        self.assertEqual(result[0][0]['Conn'], 'JD11_JPL2_1V5_M')
        self.assertEqual(result[0][-1]['Descr'], 'GND')


if __name__ == '__main__':
    unittest.main()
