#!/bin/bash
set -euo pipefail
function error() { echo $@ >&2; exit 1; }

usage() {
  echo "Please use one of the following commands (not all implemented yet):"
  echo
  echo "import-collection ID"
  echo "receive-collection ID"
  echo "load-collection ID"
  echo
  echo "import-terminology ID"
  echo "receive-collection ID"
  echo "load-terminology ID"
}

# TODO: check for existence of ./stage etc.

usage
