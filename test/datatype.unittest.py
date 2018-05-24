#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 02:22 PM -0400

import unittest


import sys
sys.path.insert(0, '..')

from utm.datatype import ColNum, range


class DataTypeTester(unittest.TestCase):
    def test_representation(self):
        self.assertEqual(ColNum('A'), ColNum('A'))
        self.assertEqual(ColNum('A'), 1)
        self.assertEqual(str(ColNum('A')), 'A')

    def test_representation_complex(self):
        self.assertEqual(ColNum('AB'), 28)
        self.assertEqual(ColNum('ABC'), 731)

    def test_inequalities(self):
        self.assertLessEqual(ColNum('A'), ColNum('B'))
        self.assertGreaterEqual(ColNum('ABC'), ColNum('AB'))

    def test_summation(self):
        self.assertEqual(ColNum('A') + 1, ColNum('B'))
        self.assertEqual(ColNum('A') + ColNum('B'), ColNum('C'))
        self.assertEqual(ColNum('A')*26*26 + ColNum('BC'), ColNum('ABC'))

    def test_summation_representation(self):
        self.assertEqual(str(ColNum('A') + 1), str(ColNum('B')))
        self.assertEqual(str(ColNum('A') + ColNum('B')), str(ColNum('C')))
        self.assertEqual(str(ColNum('A')*26*26 + ColNum('BC')),
                         str(ColNum('ABC')))

    def test_inplace_summation(self):
        num = ColNum('A')
        num += 1
        self.assertEqual(num, 2)
        self.assertEqual(str(num), 'B')

    def test_string_representation(self):
        self.assertEqual(str(ColNum('A'))+str(1), 'A1')

    def test_range_generation(self):
        self.assertEqual(range(ColNum('A'), ColNum('E')), [1, 2, 3, 4])
        self.assertEqual(str(range(ColNum('A'), ColNum('E'))[1]), 'B')


if __name__ == '__main__':
    unittest.main()
