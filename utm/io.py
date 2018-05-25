#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu May 24, 2018 at 09:37 PM -0400

import openpyxl
import re

from utm.datatype import range, ColNum


def parse_cell_range(s, add_one_to_trailing_cell=True):
    initial, final = s.split(':')
    initial_col, initial_row = filter(None, re.split(r'(\d+)', initial))
    final_col, final_row = filter(None, re.split(r'(\d+)', final))

    if add_one_to_trailing_cell:
        return (ColNum(initial_col.upper()), int(initial_row),
                ColNum(final_col.upper())+1, int(final_row)+1)
    else:
        return (ColNum(initial_col.upper()), int(initial_row),
                ColNum(final_col.upper()), int(final_row))


class XLReader(object):
    def __init__(self, filename, sheets, cell_range,
                 sortby=None):
        # Note: we assume the first row is the header line.
        self.wb = openpyxl.load_workbook(filename, read_only=True)

        self.initial_col, self.initial_row, self.final_col, self.final_row = \
            parse_cell_range(cell_range)

        self.sheets = sheets
        self.sortby = sortby

    def read(self):
        result = []
        for s in self.sheets:
            result.append(self.readsheet(str(s)))
        return result

    def readsheet(self, sheet_name):
        sheet = self.wb[sheet_name]

        # Read the first row as headers, determine non-empty headers;
        # for all subsequent rows, skip columns without a header.
        non_empty_col = dict()
        for col in range(self.initial_col, self.final_col):
            anchor = str(col) + str(self.initial_row)
            header = sheet[anchor].value
            if header is not None:
                # Note: some of the title contain '\n'. We replace it with an
                # space.
                non_empty_col[str(col)] = header.replace('\n', ' ')

        # Now read the real data
        data = []
        for row in range(self.initial_row+1, self.final_row):
            pin_spec = dict()
            for col in non_empty_col.keys():
                anchor = str(col) + str(row)
                pin_spec[non_empty_col[col]] = sheet[anchor].value
            data.append(pin_spec)

        if self.sortby is not None:
            pass

        else:
            return data
