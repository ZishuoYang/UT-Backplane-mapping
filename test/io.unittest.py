#!/usr/bin/env python
#
# License: MIT
# Last Change: Wed Aug 29, 2018 at 04:44 PM -0400

import unittest
from pathlib import Path

import sys
sys.path.insert(0, '..')

from pyUTM.io import generate_csv_line
from pyUTM.io import parse_cell_range, XLReader

input_dir = Path('..') / Path('input')
pt_filename = input_dir / Path(
    'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')
brkoutbrd_filename = input_dir / Path(
    'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')


class GenerateCsvLineTester(unittest.TestCase):
    def test_normal_entry(self):
        entry = (1, 2, 3, 4, 5)
        self.assertEqual(generate_csv_line(entry), '1,2,3,4,5')

    def test_entry_with_none(self):
        entry = (1, 2, 3, 4, None)
        self.assertEqual(generate_csv_line(entry), '1,2,3,4,')

    def test_entry_with_none_alt(self):
        entry = (1, 2, 3, 4, None)
        self.assertEqual(generate_csv_line(entry, ignore_empty=False),
                         '1,2,3,4,None')


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

    def test_read_sort_with_headers_single_spec(self):
        reader = XLReader(brkoutbrd_filename)
        headers = {'A': 'Conn', 'D': 'Descr'}
        result = reader.read(['PinAssignments'], 'A4:D18', headers=headers,
                             sortby=lambda item: item['Conn'])
        self.assertEqual(result[0][0]['Conn'], 'GND')
        # FIXME: '9' will come after '11'
        self.assertEqual(result[0][3]['Conn'], 'JD11_10_JPL2_2V5')
        self.assertEqual(result[0][-1]['Conn'], 'JP11_JPL2_P4_LV_SOURCE')


if __name__ == '__main__':
    unittest.main()
