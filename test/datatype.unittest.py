#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 06:44 AM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.datatype import ColNum, range


class DataTypeTester(unittest.TestCase):
    def test_representation(self):
        self.assertEqual(ColNum('A'), ColNum('A'))
        self.assertEqual(ColNum('A'), 1)
        self.assertEqual(str(ColNum('A')), 'A')

    def test_representation_complex(self):
        self.assertEqual(ColNum('AB'), 28)
        self.assertEqual(ColNum('ABC'), 731)

    def test_representation_of_zero(self):
        self.assertEqual(ColNum('0'), 0)
        self.assertEqual(ColNum('AB') - ColNum('AB'), 0)

    def test_backward_representation(self):
        lst = [0, 1, 2, 3]
        self.assertEqual(int(ColNum('A')), 1)
        self.assertEqual(lst[ColNum('C')], 3)

    def test_inequalities(self):
        self.assertLessEqual(ColNum('A'), ColNum('B'))
        self.assertGreaterEqual(ColNum('ABC'), ColNum('AB'))

    def test_addition(self):
        self.assertEqual(ColNum('A') + 1, ColNum('B'))
        self.assertEqual(ColNum('A') + ColNum('B'), ColNum('C'))
        self.assertEqual(ColNum('A')*26*26 + ColNum('BC'), ColNum('ABC'))

    def test_addition_representation(self):
        self.assertEqual(str(ColNum('A') + 1), str(ColNum('B')))
        self.assertEqual(str(ColNum('A') + ColNum('B')), str(ColNum('C')))
        self.assertEqual(str(ColNum('A')*26*26 + ColNum('BC')),
                         str(ColNum('ABC')))

    def test_subtraction(self):
        self.assertEqual(ColNum('B') - ColNum('A'), 1)
        self.assertEqual(str(ColNum('B') - ColNum('A')), 'A')
        self.assertEqual(ColNum('A') - ColNum('B'), 1)
        self.assertEqual(str(ColNum('A') - ColNum('B')), 'A')

    def test_inplace_additon(self):
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
