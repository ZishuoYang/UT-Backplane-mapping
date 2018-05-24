#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 02:04 PM -0400

import unittest


import sys
sys.path.insert(0, '..')

from utm.io import parse_cell_range


class ParseCellRangeTester(unittest.TestCase):
    def test_parsing(self):
        cell_range = 'A12:CC344'
        initial_col, initial_row, final_col, final_row = parse_cell_range(
            cell_range
        )
        self.assertEqual(initial_col, 'A')
        self.assertEqual(initial_row, '12')
        self.assertEqual(final_col, 'CC')
        self.assertEqual(final_row, '344')

    def test_parsing_make_upper(self):
        cell_range = 'a12:cC344'
        initial_col, initial_row, final_col, final_row = parse_cell_range(
            cell_range
        )
        self.assertEqual(initial_col, 'A')
        self.assertEqual(initial_row, '12')
        self.assertEqual(final_col, 'CC')
        self.assertEqual(final_row, '344')


if __name__ == '__main__':
    unittest.main()
