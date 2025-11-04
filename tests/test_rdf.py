import pytest

from lib import triple_iterator, RDFFilter


class LogMock:
    def append(self, msg):
        pass


def parse(source, filter=None, unique=False):
    triples = [(s, p, o) for s, p, o in triple_iterator(source, LogMock())]
    if filter:
        triples = [t for t in [filter.check_triple(*t) for t in triples] if type(t) == list]
    if unique:
        triples = [list(t) for t in set(tuple(t) for t in triples)]
    return triples


def test_parsing():
    with pytest.raises(Exception):
        parse("tests/invalid.nt")

    assert len(parse("tests/skos.rdf")) == 377
    assert len(parse("tests/rdf.zip")) == 4


def test_filter():
    triples = parse("tests/filter.ttl")
    assert len(triples) == 6

    filter = RDFFilter(disallow_subject_ns=('http://www.cidoc-crm.org/cidoc-crm/'))
    triples = parse("tests/filter.ttl", filter, True)
    assert len(triples) == 2
