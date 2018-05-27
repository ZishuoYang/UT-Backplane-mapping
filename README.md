# UT-Backplane-mapping [![Build status](https://travis-ci.com/ypsun-umd/UT-Backplane-mapping.svg?master)](https://travis-ci.com/ypsun-umd)
Signal mapping netlist (list of pin-to-pin correspondence) formatted for Altium to design the LHCb UT backplane.

This script takes 3 MS Excel files and write the reformatted list to `gen/`.
All MS Excel files are located under `templates/`;
one of them describes connections from PT connectors point-of-view (`PT->DCB`);
another from DCB;
the third one includes break-out boards pin assignments.


## Prereuisite
```
Python: python 2.7.x
openpyxl: >= 2.5.3
```


## Usage
```
python ./AltiumNetlistGen.py
```
All generated `.csv` files are located under `gen/`.
This script prints out warnings to `stdout`, and can be redirected as needed.


## Reference
The backplane-mapping effort is documented on TWiki page: [1]

[1]: https://twiki.cern.ch/twiki/bin/view/LHCb/BackplaneMapping
