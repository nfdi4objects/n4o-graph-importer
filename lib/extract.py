from .walk import walk
import lightrdf

rdfparser = lightrdf.Parser()


def extractRDF(source):
    """Recursively extract RDF triples from a file, directory and/or ZIP archive."""
    for name, path, archive in walk(source):
        format = None
        if name.endswith(".ttl"):
            format = "turtle"
        elif name.endswith(".nt"):
            format = "nt"
        elif name.endswith(".owl"):
            format = "owl"
        elif name.endswith(".rdf"):
            format = "xml"
        else:
            # TODO: support more RDF serialization formats, in particular RDF/XML
            continue

        if archive:
            file = archive.open(name)
            base = f"file://{file.name}"
        else:
            file = f"{source}/{name}"
            base = f"file://{file}"

        # base = None # TODO
        # print(file, base)

        try:
            for triple in rdfparser.parse(file, format=format):
                yield triple
        except Exception as e:
            print(f"Error parsing {file}: {e} {base}")
            continue
