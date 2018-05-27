#!/usr/bin/env python
#
# License: MIT
# Last Change: Sun May 27, 2018 at 03:02 PM -0400

import openpyxl
import re

from pyUTM.datatype import range, ColNum


def write_to_csv(filename, data):
    with open(filename, 'w') as f:
        for entry in data:
            f.write(generate_csv_line(entry) + '\n')


def generate_csv_line(entry, ignore_empty=True):
    s = ''
    for cell in entry:
        if cell is not None:
            s += str(cell)
        elif not ignore_empty:
            s += 'None'
        s += ','
    # Remove the trailing ','
    return s[:-1]


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
    def __init__(self, filename):
        self.wb = openpyxl.load_workbook(filename, read_only=True)

    def read(self, sheets, cell_range, sortby=None, headers=None):
        self.sheets = sheets
        self.cell_range = cell_range
        self.initial_col, self.initial_row, self.final_col, self.final_row = \
            parse_cell_range(cell_range)

        result = []
        for s in self.sheets:
            result.append(self.readsheet(str(s),
                                         sortby=sortby, headers=headers))
        return result

    def readsheet(self, sheet_name, sortby, headers):
        # We read the full rectangular region to build up a cache. Otherwise if
        # we read one cell at a time, all cells prior to that cell must be read,
        # rendering that method VERY inefficient.
        sheet_region = self.wb[sheet_name][self.cell_range]
        sheet = dict()
        for row in range(self.initial_row, self.final_row):
            for col in range(self.initial_col, self.final_col):
                sheet[str(col)+str(row)] = \
                    sheet_region[row-self.initial_row][col-self.initial_col]

        if headers is not None:
            data = self.get_data_header_supplied(sheet, headers)
        else:
            data = self.get_data_header_not_supplied(sheet)

        if sortby is not None:
            return sorted(data, key=sortby)
        else:
            return data

    def get_data_header_not_supplied(self, sheet):
        # Read the first row as headers, determine non-empty headers;
        # for all subsequent rows, skip columns without a header.
        headers_non_empty_col = dict()
        for col in range(self.initial_col, self.final_col):
            anchor = str(col) + str(self.initial_row)
            header = sheet[anchor].value
            if header is not None:
                # Note: some of the title contain '\n'. We replace it with an
                # space.
                headers_non_empty_col[str(col)] = header.replace('\n', ' ')

        return self.get_data_header_supplied(sheet, headers_non_empty_col,
                                             initial_row_bump=1)

    def get_data_header_supplied(self, sheet, headers, initial_row_bump=0):
        data = []
        for row in range(self.initial_row+initial_row_bump, self.final_row):
            pin_spec = dict()
            for col in headers.keys():
                anchor = str(col) + str(row)
                pin_spec[headers[col]] = sheet[anchor].value
            data.append(pin_spec)
        return data
