#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Dec 06, 2018 at 12:07 PM -0500

import unittest
import re
# from math import factorial

import sys
sys.path.insert(0, '..')

from pyUTM.common import transpose, flatten, unflatten


class YamlHelper(unittest.TestCase):
    def test_transpose(self):
        test_list = [
            {'Tom': 1, 'Tim': 2}, {'Tom': 3, 'Tim': 4}, {'Tom': 5, 'Tim': 6}]
        self.assertEqual(transpose(test_list),
                         {'Tom': [1, 3, 5], 'Tim': [2, 4, 6]})

    def test_flatten_default_header(self):
        test_list_dict = [
            {'Some':  {'A': 1, 'B': 2}},
            {'Stuff': {'A': 3, 'B': 4}},
        ]
        self.assertEqual(
            flatten(test_list_dict),
            [
                {'PlaceHolder': 'Some', 'A': 1, 'B': 2},
                {'PlaceHolder': 'Stuff', 'A': 3, 'B': 4},
            ]
        )

    def test_flatten_custom_header(self):
        test_list_dict = [
            {'Some':  {'A': 1, 'B': 2}},
            {'Stuff': {'A': 3, 'B': 4}},
        ]
        self.assertEqual(
            flatten(test_list_dict, header='Custom'),
            [
                {'Custom': 'Some', 'A': 1, 'B': 2},
                {'Custom': 'Stuff', 'A': 3, 'B': 4},
            ]
        )

    def test_unflatten(self):
        test_list_dict = [
            {'Custom': 'Some', 'A': 1, 'B': 2},
            {'Custom': 'Stuff', 'A': 3, 'B': 4},
        ]
        self.assertEqual(
            unflatten(test_list_dict, 'Custom'),
            [
                {'Some':  {'A': 1, 'B': 2}},
                {'Stuff': {'A': 3, 'B': 4}},
            ]
        )


if __name__ == '__main__':
    unittest.main()
