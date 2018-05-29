#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue May 29, 2018 at 03:58 PM -0400

import __builtin__
from string import ascii_uppercase


def range(*args):
    if isinstance(args[0], ColNum):
        return [ColNum(to_str(i)) for i in __builtin__.range(*args)]
    else:
        return __builtin__.range(*args)


def to_num(s):
    if s == '0':
        return 0
    else:
        num = 0
        input_str = ''.join(reversed(s))

        for i in range(0, len(input_str)):
            letter = input_str[i]
            num += (ascii_uppercase.index(letter)+1) * 26**i

        return num


def to_str(n):
    if n == 0:
        return '0'
    else:
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
    def __new__(cls, s):
        num = to_num(s)
        self = int.__new__(cls, num)
        self.value = num
        self.name = s
        return self

    def __str__(self):
        return self.name

    def __add__(self, other):
        numerical = abs(self.value + other)
        return(ColNum(to_str(numerical)))

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        numerical = abs(self.value - other)
        return(ColNum(to_str(numerical)))

    def __rsub__(self, other):
        return self.__sub__(other)


class BrkStr(str):
    def __new__(cls, s):
        self = super(BrkStr, cls).__new__(cls, s)
        self.value = s
        return self

    def __contains__(self, key):
        if key in self.split_signal_id_into_three(self.value):
            return True
        else:
            return False

    @staticmethod
    def split_signal_id_into_three(id):
        # FIXME: can be written more compactly with regexp
        splitted = list()
        encountered_underscored = 0
        name = ''

        for char in id:
            if char is '_':
                if encountered_underscored < 2:
                    splitted.append(name)
                    name = ''
                else:
                    name += char
                encountered_underscored += 1
            else:
                name += char

        splitted.append(name)
        return splitted
