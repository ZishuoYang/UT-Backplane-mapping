#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 03:32 AM -0400

from string import ascii_uppercase


def to_num(s):
    pass


class BaseTSNum(int):
    def __new__(cls, s):
        self = int.__new__(cls, to_num(s))
        self.name = s

    def __str__(self):
        return self.name
