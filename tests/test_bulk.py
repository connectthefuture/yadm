import pytest

from pymongo.errors import BulkWriteError

from yadm import fields
from yadm.documents import Document
from yadm.bulk import Bulk


class Doc(Document):
    __collection__ = 'docs'

    i = fields.IntegerField()


@pytest.fixture
def index(db):
    return db.db.docs.ensure_index([('i', 1)], unique=True)


def test_create(db):
    bulk = db.bulk(Doc)
    assert isinstance(bulk, Bulk)


def test_insert_one(db):
    doc = Doc()
    doc.i = 1

    bulk = db.bulk(Doc)
    bulk.insert(doc)

    assert db.db.docs.count() == 0

    bulk.execute()

    assert bulk.result
    assert db.db.docs.count() == 1
    assert db.db.docs.find_one()['i'] == 1


def test_insert_many(db):
    bulk = db.bulk(Doc)

    for i in range(10):
        doc = Doc()
        doc.i = i
        bulk.insert(doc)

    assert db.db.docs.count() == 0
    bulk.execute()
    assert db.db.docs.count() == 10


def test_insert_type_error(db):
    class OtherDoc(Document):
        __collection__ = 'otherdocs'

    bulk = db.bulk(Doc)

    with pytest.raises(TypeError):
        bulk.insert(OtherDoc())


def test_context_manager(db):
    with db.bulk(Doc) as bulk:
        doc = Doc()
        doc.i = 1
        bulk.insert(doc)

    assert db.db.docs.count() == 1


def test_context_manager_error(db):
    with pytest.raises(RuntimeError):
        with db.bulk(Doc) as bulk:
            doc = Doc()
            doc.i = 1
            bulk.insert(doc)

            raise RuntimeError

    assert db.db.docs.count() == 0


def test_result(db):
    with db.bulk(Doc) as bulk:
        doc = Doc()
        doc.i = 1
        bulk.insert(doc)

    assert bulk.result.n_inserted == 1


def test_result_write_error(db, index):
    with db.bulk(Doc, raise_on_errors=False) as bulk:
        doc = Doc()
        doc.i = 1
        bulk.insert(doc)

        doc = Doc()
        doc.i = 2
        bulk.insert(doc)

        doc = Doc()
        doc.i = 1
        bulk.insert(doc)

    assert not bulk.result
    assert db.db.docs.count() == 2
    assert bulk.result.n_inserted == 2
    assert len(bulk.result.write_errors) == 1
    assert bulk.result.write_errors[0].document.i == 1


def test_result_write_error_raise(db, index):
    with pytest.raises(BulkWriteError):
        with db.bulk(Doc) as bulk:
            doc = Doc()
            doc.i = 1
            bulk.insert(doc)

            doc = Doc()
            doc.i = 2
            bulk.insert(doc)

            doc = Doc()
            doc.i = 1
            bulk.insert(doc)

    assert bulk.result.n_inserted == 2
    assert len(bulk.result.write_errors) == 1
    assert bulk.result.write_errors[0].document.i == 1


def test_result_write_error_ordered(db, index):
    with db.bulk(Doc, ordered=True, raise_on_errors=False) as bulk:
        for i in range(10):
            doc = Doc()
            doc.i = i
            bulk.insert(doc)

            doc = Doc()
            doc.i = 1
            bulk.insert(doc)

    assert db.db.docs.count() == 2
    assert bulk.result.n_inserted == 2
    assert len(bulk.result.write_errors) == 1
    assert bulk.result.write_errors[0].document.i == 1
