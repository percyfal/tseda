import os

import panel as pn
import pytest
import tskit
from click.testing import CliRunner

from tseda import datastore, model

dirname = os.path.abspath(os.path.dirname(__file__))

PORT = [6000]


@pytest.fixture
def port():
    PORT[0] += 1
    return PORT[0]


@pytest.fixture(autouse=True)
def server_cleanup():
    """
    Clean up server state after each test.
    """
    try:
        yield
    finally:
        pn.state.reset()


@pytest.fixture
def treesfile():
    return os.path.join(dirname, "data/test.trees")


@pytest.fixture
def tszipfile():
    return os.path.join(dirname, "data/test.trees.tsz")


@pytest.fixture
def tsbrowsefile():
    return os.path.join(dirname, "data/test.trees.tsbrowse")


@pytest.fixture
def tsedafile():
    return os.path.join(dirname, "data/test.trees.tseda")


@pytest.fixture
def ts(treesfile):
    return tskit.load(treesfile)


@pytest.fixture
def tsm(tsedafile):
    return model.TSModel(tsedafile)


@pytest.fixture
def ds(tsm):
    return datastore.DataStore(tsm=tsm)


@pytest.fixture(scope="function")
def runner():
    """Base client runner."""
    return CliRunner()
