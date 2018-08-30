#!/usr/bin/env python
#
# License: MIT
# Last Change: Thu Aug 30, 2018 at 05:14 PM -0400

import openpyxl
import re

from pyparsing import nestedExpr

from pyUTM.datatype import range, ColNum
from pyUTM.selection import RulePD


##################
# For CSV output #
##################

def generate_csv_line(node, attr):
    s = ''

    if node.NET_NAME is None:
        s += attr
    elif attr is not None:
        net_head, net_tail = node.NET_NAME.split('_', 1)
        s += (net_head + attr + net_tail)
    else:
        s += node.NET_NAME
    s += ','

    for item in node[1:]:
        if item is not None:
            s += item
        s += ','

    # Remove the trailing ','
    return s[:-1]


def write_to_csv(filename, data, formatter=generate_csv_line):
    with open(filename, 'w') as f:
        for node in data.keys():
            attr = data[node]
            f.write(formatter(node, attr) + '\n')


#######################
# For Excel documents #
#######################

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
        self.filename = filename

    def read(self, sheets, cell_range, sortby=None, headers=None):
        self.sheets = sheets
        self.cell_range = cell_range
        self.initial_col, self.initial_row, self.final_col, self.final_row = \
            parse_cell_range(cell_range)

        result = []
        # FIXME: currently openpyxl throws out a warning about unclosed files.
        # This is due to a bug #673 of the openpyxl.
        wb = openpyxl.load_workbook(self.filename, read_only=True)
        for s in self.sheets:
            ws = wb[str(s)]
            result.append(self.readsheet(ws, sortby=sortby, headers=headers))
        wb.close()
        return result

    def readsheet(self, ws, sortby, headers):
        # We read the full rectangular region to build up a cache. Otherwise if
        # we read one cell at a time, all cells prior to that cell must be read,
        # rendering that method VERY inefficient.
        sheet_region = ws[self.cell_range]
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


####################
# For Pcad netlist #
####################

class NestedListReader(object):
    def __init__(self, filename):
        self.filename = filename

    def read(self):
        return nestedExpr().parseFile(self.filename).asList()[0]


class PcadReader(NestedListReader):
    def read(self):
        nested_list = super().read()

        all_nets_dict = {}
        for item in nested_list:
            # Get the nets from nestedList
            if type(item) == list and item[0] == 'net':
                net_dict = {}
                net = []
                net_attr = []
                net_name = item[1].strip('\"')
                for sublist in item:
                    if type(sublist) == list:
                        if sublist[0] == 'node':
                            # Add node to the net
                            net.append([sublist[1].strip('\"'),
                                        sublist[2].strip('\"')])
                        elif sublist[0] == 'attr':
                            net_attr.append(sublist[1].strip('\"'))
                        else:
                            continue
                # Sort nodes according to pin
                net = sorted(net, key=lambda x: x[1])
                net_dict['net'] = net
                net_dict['attr'] = net_attr
                all_nets_dict[net_name] = net_dict
        return all_nets_dict
