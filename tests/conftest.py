import os

import pytest
import tskit

from tseda import model

dirname = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def ts():
    return tskit.load(os.path.join(dirname, "data/test.trees"))


@pytest.fixture
def tsm(ts):
    return model.TSEdaModel(ts)


@pytest.fixture
def tsm2(tsm):
    """Remove outgroup individuals from model"""
    tsm.toggle_individual(18)
    tsm.toggle_individual(19)
    tsm.toggle_individual(20)
    return tsm
