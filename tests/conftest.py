import os

import tskit
from pytest import fixture

from tseda import model

dirname = os.path.abspath(os.path.dirname(__file__))


@fixture
def treesfile():
    return os.path.join(dirname, "data/test.trees")


@fixture
def ts(treesfile):
    return tskit.load(treesfile)


@fixture
def tsm(ts):
    return model.TSEdaModel(ts)


@fixture
def tsmh(tsm):
    """Remove outgroup individuals from model to include only Homo
    Sapiens individuals"""
    tsm.toggle_individual(18)
    tsm.toggle_individual(19)
    tsm.toggle_individual(20)
    return tsm
