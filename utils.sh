set -euo pipefail

error() {
    echo $@ >&2
    exit 1
}

require_bartoc_id() {
    [[ $# -ge 1 ]] || error "Missing BARTOC URI or ID"

    if [[ "$1" =~ ^[0-9]+$ ]]; then
        id=$1
    elif [[ "$1" =~ ^https?://bartoc.org/en/node/[0-9]+$ ]]; then
        id="${1##*/}"
    else
        error "Invalid BARTOC URI or ID!"
    fi
    uri=http://bartoc.org/en/node/$id
}

require_collection_id() {
    [[ $# -ge 1 ]] || error "Missing collection ID"
    [[ "$1" =~ ^[0-9]*$ ]] || error "Collection ID must be numeric!"
    id=$1
    uri=https://graph.nfdi4objects.net/collection/$1
}

SPARQL=${SPARQL:-http://localhost:3030/n4o}
SPARQL_UPDATE=${SPARQL_UPDATE:-$SPARQL}
SPARQL_STORE=${SPARQL_STORE:-$SPARQL}
STAGE=${STAGE:-stage}
