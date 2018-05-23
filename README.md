# UT-Backplane-mapping

Signal mapping netlist (list of pin-to-pin correspondence) formatted for Altium to design the LHCb UT backplane

## Script objectives

reformat_for_Altium.py (written in Python 2.7) that reads input CSV files and prints out reformatted list
Input CSV files are one from PT connectors point-of-view (PT->DCB), and another from DCB connectors p.o.v.

## Running the script

python reformat_for_Altium.py > test_AltiumNetlist_PT.CSV

## Reference

The backplane-mapping effort is documented on TWiki page: https://twiki.cern.ch/twiki/bin/view/LHCb/BackplaneMapping

