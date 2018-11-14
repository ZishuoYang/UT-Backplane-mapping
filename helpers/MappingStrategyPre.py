#!/usr/bin/env python
#
# License: MIT
# Last Change: Tue Nov 13, 2018 at 07:01 PM -0500

import yaml

from pathlib import Path

import sys
sys.path.insert(0, '..')

input_dir  = Path('..') / Path('input')
output_dir = Path('..') / Path('output')

strategy_yaml_filename = input_dir / Path('mapping_strategy.yml')
strategy_tex_filename  = output_dir / Path('mapping_strategy.tex')


###########
# Helpers #
###########
