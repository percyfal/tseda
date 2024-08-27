import json

import numpy as np
import pytest

from tseda import model


def test_individual(ts):
    ind = model.Individual(individual=ts.individual(0))
    assert ind is not None
    assert ind.id == 0
    assert ind.population == 1
    assert ind.metadata is not None
    np.testing.assert_equal(ind.samples, [0, 1])
    with pytest.raises(TypeError):
        ind = model.Individual()


def test_sample(ts):
    sample = model.Sample(node=ts.node(0))
    assert sample is not None
    assert sample.id == 0
    assert sample.population == 1
    assert sample.metadata is not None
    assert sample.sample_set_id == 1
    assert sample.is_sample()
    with pytest.raises(TypeError):
        sample = model.Sample()


def test_sample_set_init(ts):
    for pop in ts.populations():
        ss = model.SampleSet(pop.id, population=pop)
        assert ss is not None
        assert ss.id == pop.id
        assert ss.name == json.loads(pop.metadata.decode())["population"]
        assert ss.color == ss.colormap[pop.id]


def test_update_individual_sample_set(tsm):
    tsm.update_individual_sample_set(0, 1)
    assert tsm.individuals[0].sample_set_id == 1
    assert tsm.samples[tsm.individuals[0].samples[0]].sample_set_id == 1
    assert tsm.samples[tsm.individuals[0].samples[1]].sample_set_id == 1
    tsm.update_individual_sample_set(0, 0)
    assert tsm.individuals[0].sample_set_id == 0
    assert tsm.samples[tsm.individuals[0].samples[0]].sample_set_id == 0
    assert tsm.samples[tsm.individuals[0].samples[1]].sample_set_id == 0


def test_toggle_individual(tsm):
    assert tsm.individuals[0].selected
    assert tsm.samples[tsm.individuals[0].samples[0]].selected
    assert tsm.samples[tsm.individuals[0].samples[1]].selected
    tsm.toggle_individual(0)
    assert not tsm.individuals[0].selected
    assert not tsm.samples[tsm.individuals[0].samples[0]].selected
    assert not tsm.samples[tsm.individuals[0].samples[1]].selected
    tsm.toggle_individual(0)
    assert tsm.individuals[0].selected
    assert tsm.samples[tsm.individuals[0].samples[0]].selected
    assert tsm.samples[tsm.individuals[0].samples[1]].selected


def test_gnn(tsm2):
    gnn = tsm2.gnn()
    assert gnn is not None
    assert gnn.shape == (36, 3)
    assert sorted(gnn.index.names) == sorted(
        ["sample_set_id", "sample_id", "id"]
    )
    assert sorted(gnn.columns.values) == [0, 1, 2]


def test_get_samples(tsm):
    with pytest.raises(ValueError):
        samples = tsm.get_samples(astype="gdf")
    samples = tsm.get_samples()
    assert samples is not None
    for i, sample in enumerate(samples):
        assert sample.id == i
    assert samples[0].population == 1
    assert samples[0].metadata is not None
    assert samples[0].sample_set_id == 1
    assert samples[8].id == 8
    data = tsm.get_samples(astype="df")
    assert data is not None
    assert data.shape == (42, 7)


def test_get_individuals(tsm):
    individuals = tsm.get_individuals()
    assert individuals is not None
    for i, ind in enumerate(individuals):
        assert individuals[i].id == i
    assert individuals[0].population == 1
    assert individuals[0].metadata is not None
    assert individuals[0].sample_set_id == 1
    data = tsm.get_individuals(astype="df")
    assert data is not None
    assert data.shape == (21, 11)
    data = tsm.get_individuals(astype="gdf")
    assert data is not None
    assert data.shape == (21, 10)
    assert "geometry" in data.columns
