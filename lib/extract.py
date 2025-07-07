from .walk import walk
import lightrdf

rdfparser = lightrdf.Parser()


def extractRDF(source):
    """Recursively extract RDF triples from a file, directory and/or ZIP archive."""
    for name, path, archive in walk(source):
        format = None
        if name.endswith(".ttl") or name.endswith(".nt"):
            format = "turtle"
        elif name.endswith(".owl"):
            format = "owl"
        else:
            # TODO: support more RDF serialization formats, in particular RDF/XML
            continue

        if archive:
            file = archive.open(name)
            base = f"file://{name}"
        else:
            file = f"{source}/{name}"
            base = f"file://{file}"

        base = None # TODO
        print(file)

        try:
            for triple in rdfparser.parse(file, base_iri=base, format=format):
                yield triple
        except Exception as e:
            path.reverse()
            raise Exception(f"{e} of {name} in " + " in ".join(path))
