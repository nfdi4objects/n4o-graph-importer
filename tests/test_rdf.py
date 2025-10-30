import pytest

from lib import triple_iterator

class LogMock:
    def append(self, msg):
        pass

def test_parsing():
    with pytest.raises(Exception):
        triples = [*triple_iterator("tests/invalid.nt", LogMock())]

    triples = [*triple_iterator("tests/skos.rdf", LogMock())]
    assert len(triples) == 377

    triples = [*triple_iterator("tests/rdf.zip", LogMock())]
    assert len(triples) == 4

