import os

import panel as pn
import tskit
from pytest import fixture
from tseda import model

from tseda import datastore

dirname = os.path.abspath(os.path.dirname(__file__))

PORT = [6000]


@fixture
def port():
    PORT[0] += 1
    return PORT[0]


@fixture(autouse=True)
def server_cleanup():
    """
    Clean up server state after each test.
    """
    try:
        yield
    finally:
        pn.state.reset()


@fixture
def treesfile():
    return os.path.join(dirname, "data/test.trees")


@fixture
def tszipfile():
    return os.path.join(dirname, "data/test.trees.tsz")


@fixture
def tsbrowsefile():
    return os.path.join(dirname, "data/test.trees.tsbrowse")


@fixture
def tsedafile():
    return os.path.join(dirname, "data/test.trees.tseda")


@fixture
def ts(treesfile):
    return tskit.load(treesfile)


@fixture
def tsm(tsedafile):
    return model.TSModel(tsedafile)


@fixture
def ds(tsm):
    individuals_table, sample_sets_table = datastore.preprocess(tsm)
    return datastore.DataStore(
        tsm=tsm,
        individuals_table=individuals_table,
        sample_sets_table=sample_sets_table,
    )
