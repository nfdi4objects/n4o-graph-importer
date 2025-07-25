#!/usr/local/bin/python3

"""Extract all RDF turtle files from a directory. Supports .nt and .ttl files."""
import sys
import os
from lib import extractRDF


def main(args):
    if len(args) != 2:
        print("Please provide a source directory and a target file`")
        sys.exit(1)

    source, target = args
    if not os.path.isdir(source):
        print(f"Directory does not exist: {source}")
        sys.exit(1)

    if os.path.isdir(target):
        print(f"Target must not be a directory: {target}")
        sys.exit(1)

    triples = 0
    tmp = "tmp.nt"
    with open(target, "w") as out:
        for triple in extractRDF(source):
            print(" ".join(triple) + " .", file=out)
            triples += 1

    if triples:
        print(f"extracted {triples} triples into {target}")
    else:
        print("No RDF found!")
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
