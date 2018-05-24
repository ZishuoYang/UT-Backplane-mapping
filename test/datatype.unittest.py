#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 03:33 AM -0400

import unittest

from os.path import join

import sys
sys.path.insert(0, join('..', 'utm'))

from utm.datatype import BaseTSNum


class DataTypeTester(unittest.TestCase):
    def test_representation(self):
        self.assertEqual(BaseTSNum('A'), 1)

    def test_representation_complex(self):
        self.assertEqual(BaseTSNum('AA'), 27)
        self.assertEqual(BaseTSNum('ABC'), 27)


if __name__ == '__main__':
    unittest.main()
