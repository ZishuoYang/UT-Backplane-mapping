# UT-Backplane-mapping [![Build status](https://travis-ci.com/ZishuoYang/UT-Backplane-mapping.svg?master)](https://travis-ci.com/ZishuoYang)
Signal mapping netlist (list of pin-to-pin correspondence) formatted for Altium
to design the LHCb UT backplane.

* `AltiumNetlistGen.py`: This script takes 3 YAML files and write the
  reformatted list to `output/`.  All YAML files are located under `input/`;
  one of them describes connections from PT connectors point-of-view (`PT-
  DCB`); another from DCB; the third one includes break-out boards pin
  assignments.
* `NetlistCheck.py`: This scripts takes Altium-exported netlists (under
  `input/netlists`) and check if these netlists fully implements connections
  specified in the copy-paste lists generated by the script above.


## Prerequisite
Install the dependencies:
```
pip install -r pyUTM/requirements.txt
```


## Usage
If only the copy-and-paste `.csv` are needed:
```
python ./AltiumNetlistGen.py
```

If additional error checking is required (note that this script would also
generate `.csv` files):
```
python ./NetlistCheck.py | tee ./WARNINGS.log
```

All generated `.csv` files are located under `output/`.
These scripts print out warnings to `stdout`, and can be redirected as needed.


## Reference
The backplane-mapping effort is documented on TWiki page: [1]

[1]: https://twiki.cern.ch/twiki/bin/view/LHCb/BackplaneMapping
