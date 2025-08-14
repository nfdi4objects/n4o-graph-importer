import sys
import os
from lib import CollectionRegistry

stage = os.getenv('STAGE', 'stage')

registry = CollectionRegistry(stage)

def receive(id, url=None, format=None):
    col = registry.get(id)

    if "access" in col:
        if not url:
            url = col["access"].get("url")
        if not format:
            format = col["access"].get("format")

    format = format.removeprefix('https://format.gbv.de/')
    if not format:
        format = "rdf"
    if format != "rdf":
        raise Exception(f"Only RDF data supported so far, got {format}")
    if not url:
        raise Exception(f"Missing url to receive from")

    print(f"Receive {format} data from {url}")

    # TODO: migrate from bash script to Python
    """
    # TODO: support OAI-PMH for LIDO/XML
    inbox=$STAGE/inbox/$id
    download_dir=$stage/download

    rm -rf $download_dir
    mkdir -p $download_dir

    if [[ $url == *doi.org* ]]; then
      ./download-from-repository.py $url $download_dir
    elif [[ $url == http* ]]; then
      wget -q $url --directory-prefix $download_dir
    elif [[ -d $inbox ]]; then
      cp $inbox/* $download_dir
    else
      error "No valid source $url"
    fi

    # TODO: support LIDO/XML via repository
    ./extract-rdf.py $download_dir $stage/triples.nt
    ./transform-rdf $stage/triples.nt     # includes validation
    """

if __name__ == '__main__':
    args = sys.argv[1:]
    id = args[0]    # required

    if len(args) > 2:
        receive(id, url=args[1], format=args[2])
    else:
        receive(id)

