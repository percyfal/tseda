import numpy as np
import pytest

from tseda import datastore


@pytest.fixture
def individuals_table(tsm):
    data, _ = datastore.make_tables(tsm)
    return data


def test_datastore_make_tables(tsm):
    individuals_table, sample_sets_table = datastore.make_tables(tsm)
    assert individuals_table is not None
    assert sample_sets_table is not None
    sample_sets = individuals_table.sample_sets()
    assert len(sample_sets) == 6
    np.testing.assert_equal(sample_sets[1], np.arange(0, 12))


def test_individuals_table(individuals_table):
    ind = individuals_table.loc(5)
    assert ind is not None
    assert ind.sample_set_id == 1
    assert ind.population == 1
    assert ind["name"] == "tsk_6"
    assert ind.name == 5
    assert individuals_table.sample2ind[ind.nodes[0]] == 5
    assert individuals_table.sample2ind[ind.nodes[1]] == 5
    ss = individuals_table.sample_sets()
    assert len(ss) == 6
    assert len(ss[0]) == 12
    samples = list(individuals_table.samples())
    assert len(samples) == 42


def test_datastore(ds):
    print(ds.color)
    print(ds.sample_sets_table.color_by_name)


@pytest.mark.parametrize("tsm", ["tsm", "tsedafile"], indirect=True)
def test_init_datastore(tsm):
    ds = datastore.DataStore(tsm=tsm)
    assert ds is not None
    assert isinstance(ds.individuals_table, datastore.IndividualsTable)
    assert isinstance(ds.sample_sets_table, datastore.SampleSetsTable)
    ind = ds.individuals_table.loc(5)
    assert ind["name"] == "tsk_6"
    assert ind.name == 5
    sst = ds.sample_sets_table.data.rx.value
    sst.at[0, "name"] = "foo"
    assert ds.sample_sets_table.data.rx.value.at[0, "name"] == "foo"
