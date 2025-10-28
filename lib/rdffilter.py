from .rdf import triple_iterator


class RDFFilter:

    def __init__(self, **config):
        self.disallow_subject_ns = config.get("disallow_subject_ns", None)
        self.allow_predicate = config.get("allow_predicate", None)
        if self.allow_predicate:
            self.allow_predicate = set(f"<{uri}>" for uri in self.allow_predicate)

    def check_triple(self, s, p, o):
        if self.allow_predicate and p not in self.allow_predicate:
            return False

        if self.disallow_subject_ns and str(s)[1:].startswith(self.disallow_subject_ns):
            return False

        # TODO: implement more filtering and rewrite

        return True

    def process(self, source, keep, remove, log):
        kept, removed = 0, 0

        for s, p, o in triple_iterator(source, log):
            if self.check_triple(s, p, o):
                keep.write(f"{s} {p} {o} .\n")
                kept = kept + 1
            else:
                remove.write(f"{s} {p} {o} .\n")
                removed = removed + 1

        log.append(f"Removed {removed} triples, remaining {kept} unique triples.")

        return kept, removed, 0
