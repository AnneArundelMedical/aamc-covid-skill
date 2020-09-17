#!/bin/sh
find locale -name "*.intent" -o -name "*.dialog" -exec rm -f {} ';'
python3 genscript.py PRONING_SCRIPT.txt
