#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 02:04 PM -0400

import openpyxl
import re

from utm.datatype import range, ColNum


def parse_cell_range(s):
    initial, final = s.split(':')
    initial_col, initial_row = filter(None, re.split(r'(\d+)', initial))
    final_col, final_row = filter(None, re.split(r'(\d+)', final))
    return (initial_col.upper(), initial_row, final_col.upper(), final_row)


class XLReader(object):
    def __init__(self, filename, sheets, cell_range,
                 sortby=None):
        # Note: we assume the first row is the header.
        self.wb = openpyxl.load_workbook(filename, read_only=True)

        self.sheets = sheets
        self.cell_range = cell_range
        self.sortby = sortby

    def read(self):
        result = []
        for s in self.sheets:
            result.append(self.readsheet(s))
        return result

    def read_sheet(self, sheet):
        if self.sortby is not None:
            pass

        else:
            pass
