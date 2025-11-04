import re
from rdflib.term import URIRef
from .rdf import triple_iterator

# TODO: this should not be hardcoded here but in a config file
replace_namespaces = {
    "http://www.ics.forth.gr/isl/CRMsci/": "http://www.cidoc-crm.org/extensions/crmsci/",
    "http://www.ics.forth.gr/isl/CRMinf/": "http://www.cidoc-crm.org/extensions/crminf/",
    "http://www.ics.forth.gr/isl/CRMdig/": "http://www.cidoc-crm.org/extensions/crmdig/",
    "http://purl.org/dc/terms/": "http://purl.org/dc/elements/1.1/",
    "http://cidoc-crm.org/current/": "http://www.cidoc-crm.org/cidoc-crm/",
    "http://erlangen-crm.org/170309/": "http://www.cidoc-crm.org/cidoc-crm/",
}


class NamespaceMap:
    def __init__(self, ns):
        # sort because namespaces may overlap so long ones first
        self.namespaces = dict(sorted(ns.items(), reverse=True))

    def map(self, iri):
        for ns, mapped in self.namespaces.items():
            if iri.startswith(ns):
                if mapped:
                    if mapped == True:
                        return iri
                    else:
                        return mapped + iri[len(ns):]
                else:
                    return False
        return iri


class RDFFilter:

    def __init__(self, **config):
        self.disallow_subject_ns = config.get("disallow_subject_ns", None)
        self.allow_predicate = config.get("allow_predicate", None)
        if self.allow_predicate:
            self.allow_predicate = set(f"<{uri}>" for uri in self.allow_predicate)

        # TODO: make this configurable
        self.nsmap = NamespaceMap(replace_namespaces)

    def map(self, value):
        if value.startswith("<") and value.endswith(">"):
            iri = self.nsmap.map(value[1:-1])
            return f"<{iri}>" if iri else False

    def check_triple(self, s, p, o):

        # ignore local IRIs
        if any(iri.startswith("<file://") for iri in (s, p, o)):
            return "local URI"

        # replace IRI namespaces
        s = self.map(s)
        if not s:
            return "subject namespace"
        p = self.map(p)
        if not p:
            return "predicate namespace"
        o = self.map(o)
        if not o:
            return "object namespace"

        # disallow subject namespace
        if self.disallow_subject_ns and str(s)[1:].startswith(self.disallow_subject_ns):
            return "subject namespace not allowed"

        # only allow specific predicates
        if self.allow_predicate and p not in self.allow_predicate:
            return "predicate"

        return [s, p, o]

    def process(self, source, keep, remove, log):
        kept, removed, changed = 0, 0, 0

        for s, p, o in triple_iterator(source, log):
            t = self.check_triple(s, p, o)
            if type(t) == str:
                remove.write(f"{s} {p} {o} . # {t}\n")
                removed = removed + 1
            elif not t:
                remove.write(f"{s} {p} {o} .\n")
                removed = removed + 1
            elif t == True or t == [s, p, o]:
                keep.write(f"{s} {p} {o} .\n")
                kept = kept + 1
            else:
                remove.write(f"{s} {p} {o} .\n")
                keep.write(f"{t[0]} {t[1]} {t[2]} .\n")
                changed = changed + 1

        log.append(f"Removed {removed} triples, changed {changed} triples, kept {kept} triples.")

        return kept, removed, changed
