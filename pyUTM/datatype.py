#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 05:27 AM -0400

import __builtin__
from string import ascii_uppercase


def range(*args):
    if isinstance(args[0], ColNum):
        return [ColNum(to_str(i)) for i in __builtin__.range(*args)]
    else:
        return __builtin__.range(*args)


def to_num(s):
    num = 0
    input_str = ''.join(reversed(s))

    for i in range(0, len(input_str)):
        letter = input_str[i]
        num += (ascii_uppercase.index(letter)+1) * 26**i

    return num


def to_str(n):
    str = ''
    input_num = n

    while True:
        input_num, remainder = divmod(input_num, 26)
        if input_num == 0:
            str += ascii_uppercase[remainder-1]
            break
        if input_num <= 26:
            str += ascii_uppercase[remainder-1]
            str += ascii_uppercase[input_num-1]
            break
        else:
            str += ascii_uppercase[remainder-1]

    return ''.join(reversed(str))


class ColNum(int):
    # FIXME: There is no representation of 0.
    # FIXME: The string representation will easily underflow/overflow!
    def __new__(cls, s):
        num = to_num(s)
        self = int.__new__(cls, num)
        self.value = num
        self.name = s
        return self

    def __str__(self):
        return self.name

    def __add__(self, other):
        numerical = self.value + other
        return(ColNum(to_str(numerical)))

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        numerical = self.value - other
        return(ColNum(to_str(numerical)))

    def __rsub__(self, other):
        return self.__sub__(other)
