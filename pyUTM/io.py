#!/usr/bin/env python
#
# License: MIT
# Last Change: Mon Sep 17, 2018 at 03:19 PM -0400

import openpyxl
import re

from pyparsing import nestedExpr
# from tco import with_continuations  # Make Python do tail recursion elimination

from pyUTM.datatype import range, ColNum, NetNode


##################
# For CSV output #
##################

def csv_line(node, prop):
    s = ''
    netname = prop['NETNAME']
    attr = prop['ATTR']

    if netname is None:
        s += attr
    elif attr is not None:
        net_head, net_tail = netname.split('_', 1)
        s += (net_head + attr + net_tail)
    else:
        s += netname
    s += ','

    # This should be fine as long as 'node' is a list-like structure.
    for item in node:
        if item is not None:
            s += item
        s += ','

    # Remove the trailing ','
    return s[:-1]


def write_to_csv(filename, data, formatter=csv_line):
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
        # NOTE: The ResourcesWarning is probably due to a lack of encoding in
        # the OS. Ignore it for now.
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

# @with_continuations()
# def make_combinations(src, dest=[], self=None):
    # if len(src) == 1:
        # return dest

    # else:
        # head = src[0]
        # for i in src[1:]:
            # dest.append((head, i))
        # return self(src[1:], dest)


class NestedListReader(object):
    def __init__(self, filename):
        self.filename = filename

    def read(self):
        return nestedExpr().parseFile(self.filename).asList()[0]


class PcadReader(NestedListReader):
    def read(self):
        all_nets_dict = self.readnets()
        regex_dcb = re.compile(r'^JD\d+')
        regex_pt = re.compile(r'^JP\d+')

        net_nodes_dict = {}

        for netname in all_nets_dict.keys():
            dcb_nodes = list(filter(lambda x: regex_dcb.search(x[0]),
                                    all_nets_dict[netname]))
            pt_nodes = list(filter(lambda x: regex_pt.search(x[0]),
                                   all_nets_dict[netname]))
            other_nodes = list(
                set(all_nets_dict[netname]) - set(dcb_nodes) - set(pt_nodes)
            )

            # First, handle DCB-PT connections
            if dcb_nodes and pt_nodes:
                for d in dcb_nodes:
                    for p in pt_nodes:
                        net_nodes_dict[self.net_node_gen(d, p)] = {
                            'NETNAME': netname,
                            'ATTR': None
                        }

            # Now if we do have other components...
            if other_nodes and dcb_nodes:
                for d in dcb_nodes:
                    net_nodes_dict[self.net_node_gen(d, None)] = {
                        'NETNAME': netname,
                        'ATTR': None
                    }

            if other_nodes and pt_nodes:
                for p in pt_nodes:
                    net_nodes_dict[self.net_node_gen(None, p)] = {
                        'NETNAME': netname,
                        'ATTR': None
                    }

        return net_nodes_dict

    # Zishuo's original implementation, with some omissions.
    def readnets(self):
        all_nets_dict = {}

        # First, keep only items that are netlists
        nets = filter(lambda i: isinstance(i, list) and i[0] == 'net',
                      super().read())
        for net in nets:
            net_name = net[1].strip('\"')
            # NOTE: unlike Zishuo's original implementation, this list will not
            # be sorted
            all_nets_dict[net_name] = []

            for node in \
                    filter(lambda i: isinstance(i, list) and i[0] == 'node',
                           net):
                all_nets_dict[net_name].append(
                    tuple(map(lambda i: i.strip('\"'), node[1:3]))
                )

        return all_nets_dict

    @staticmethod
    def net_node_gen(dcb_spec, pt_spec):
        try:
            dcb, dcb_pin = dcb_spec
        except Exception:
            dcb = dcb_pin = None

        try:
            pt, pt_pin = pt_spec
        except Exception:
            pt = pt_pin = None

        return NetNode(dcb, dcb_pin, pt, pt_pin)
