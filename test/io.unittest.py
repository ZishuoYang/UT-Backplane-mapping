#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Sep 13, 2018 at 02:36 PM -0400

import unittest
from pathlib import Path

import sys
sys.path.insert(0, '..')

from pyUTM.io import csv_line
from pyUTM.io import parse_cell_range, XLReader
from pyUTM.io import make_combinations, PcadReader
from pyUTM.datatype import NetNode

input_dir = Path('..') / Path('input')
pt_filename = input_dir / Path(
    'backplaneMapping_pigtailPins_trueType_strictDepopulation_v5.1.xlsm')
brkoutbrd_filename = input_dir / Path(
    'BrkOutBrd_Pin_Assignments_Mar27_2018_PM1.xlsx')


class GenerateCsvLineTester(unittest.TestCase):
    dummy_prop = {'NETNAME': 'NET', 'ATTR': None}

    def test_normal_entry(self):
        entry = NetNode(*[str(i) for i in range(1, 5)])
        self.assertEqual(csv_line(entry, self.dummy_prop), 'NET,1,2,3,4')

    def test_entry_with_none(self):
        entry = NetNode(*[str(i) for i in range(1, 4)], None)
        self.assertEqual(csv_line(entry, self.dummy_prop), 'NET,1,2,3,')

    def test_entry_with_attr(self):
        entry = NetNode('2', '3', '4', '5')
        self.assertEqual(csv_line(entry, {'NETNAME': 'A_B', 'ATTR': '_C_'}),
                         'A_C_B,2,3,4,5')


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


class PcadReaderTester(unittest.TestCase):
    def test_net_node_gen(self):
        self.assertEqual(PcadReader.net_node_gen(None, None),
                         NetNode(None, None, None, None))
        self.assertEqual(PcadReader.net_node_gen(('JD1', '1'), None),
                         NetNode('JD1', '1', None, None))
        self.assertEqual(PcadReader.net_node_gen(None, ('JP1', '1')),
                         NetNode(None, None, 'JP1', '1'))
        self.assertEqual(PcadReader.net_node_gen(('JD1', '2'), ('JP1', '1')),
                         NetNode('JD1', '2', 'JP1', '1'))

    def test_recursive_combination_base(self):
        self.assertEqual(make_combinations([1], []), [])

    def test_recursive_combination_sample(self):
        result = make_combinations([1, 2, 3], [])
        self.assertEqual(result, [(1, 2), (1, 3), (2, 3)])


if __name__ == '__main__':
    unittest.main()
