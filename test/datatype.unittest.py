#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue May 29, 2018 at 04:01 PM -0400

import unittest

import sys
sys.path.insert(0, '..')

from pyUTM.datatype import ColNum, range
from pyUTM.datatype import BrkStr


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


class BrkStrTester(unittest.TestCase):
    def test_str_basic_function(self):
        name = BrkStr('name')
        self.assertEqual(name, 'name')
        self.assertEqual(name + '_something', 'name_something')

    def test_iteration(self):
        name = BrkStr('name')
        self.assertEqual(list(name), ['n', 'a', 'm', 'e'])

    def test_lack_of_representation(self):
        name = BrkStr('name')
        name_processed = list(name)
        self.assertEqual(isinstance(name_processed[0], str), True)
        self.assertEqual(isinstance(name_processed[0], BrkStr), False)

    def test_split_signal_id(self):
        self.assertEqual(
            BrkStr.split_signal_id_into_three('JP0_JT11_SOMETHING'),
            ['JP0', 'JT11', 'SOMETHING']
        )
        self.assertEqual(
            BrkStr.split_signal_id_into_three('JP0_JT11_SOMETHING_ELSE'),
            ['JP0', 'JT11', 'SOMETHING_ELSE']
        )
        self.assertEqual(
            BrkStr.split_signal_id_into_three('JP0_JT11_SOMETHING_ELSE_IF'),
            ['JP0', 'JT11', 'SOMETHING_ELSE_IF']
        )

    def test_overloaded_contain(self):
        name1 = BrkStr('JP1_JD12_SOME_SOME_ELSE')
        name2 = BrkStr('JP11_JD12_SOME_SOME_ELSE')
        self.assertEqual('JP1' in name1, True)
        self.assertEqual('JP1' in name2, False)
        self.assertEqual('JP11' in name2, True)
        self.assertEqual('SOME_SOME_ELSE' in name1, True)
        self.assertEqual('SOME_SOME_ELSE' in name2, True)


if __name__ == '__main__':
    unittest.main()
