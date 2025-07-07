#!/usr/bin/env python

import argparse
import datahugger
import sys

parser = argparse.ArgumentParser(
    description="Download data publicationfrom Zenodo or another repository via DOI")
parser.add_argument('doi', type=str, help="DOI")
parser.add_argument('directory', type=str,
                    help="directory where to download data")
args = parser.parse_args()

try:
    # This downloads the data publication
    # TODO: also get metadata
    datahugger.get(args.doi, args.directory)
    # TODO: generate datapackage?
except Exception as e:
    sys.exit(e)
