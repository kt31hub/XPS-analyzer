# Introduction

## Purpose
This tool is designed to analyze X-ray Photoelectron Spectroscopy (XPS) data. It streamlines the workflow from raw data import to peak fitting.

## Requirements
To run XPS-analyzer, you need **Python 3.8+** installed on your system.
The following Python libraries are required:

* **numpy**
* **pandas**
* **scipy**
* **matplotlib**
* **openpyxl** (Required for exporting results to Excel)

## Quick start
1) Install Python3 (suggestion [Python3.13](https://www.python.org/downloads/release/python-31311/))
2) Install Python libraries on command prompt
```console:pip
pip install numpy pandas scipy matplotlib openpyxl
```
3) Edit json files

・RSF.json : Relative Sensitivity Factors (please add data according to the device)

・peakfit.json : Peak fit data (please add or fill data according to the paper)

4) Run `XPS_analyzer.py` if you need, edit `XPS_analyzer.py`
