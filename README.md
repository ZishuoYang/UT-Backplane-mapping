# UT-Backplane-mapping [![Build status](https://travis-ci.com/ZishuoYang/UT-Backplane-mapping.svg?master)](https://travis-ci.com/ZishuoYang)
Signal mapping netlist (list of pin-to-pin correspondence) formatted for Altium
to design the LHCb UT backplane.

This script takes 3 MS Excel files and write the reformatted list to `output/`.
All MS Excel files are located under `input/`;
one of them describes connections from PT connectors point-of-view (`PT->DCB`);
another from DCB;
the third one includes break-out boards pin assignments.


## Prerequisite
```
Python: >= 3.7
openpyxl: >= 2.5.3
pyparsing
tco
joblib
pyyaml
```

These `Python` libraries can be installed via:
```
pip install -r requirements.txt
```


## Usage
If only the copy-and-paste `.csv` are needed:
```
python ./AltiumNetlistGen.py > WARNINGS.log
```

If additional error checking is required (note that this script would also
generate `.csv` files):
```
python ./SchematicCheck.py > ERRORS.log
```

All generated `.csv` files are located under `output/`.
These scripts print out warnings to `stdout`, and can be redirected as needed.


## Reference
The backplane-mapping effort is documented on TWiki page: [1]

[1]: https://twiki.cern.ch/twiki/bin/view/LHCb/BackplaneMapping
