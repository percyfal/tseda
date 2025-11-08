import panel as pn

from tseda.widgets.structure import IndividualGNNFigure, MeanGNNFigure

pn.extension("tabulator")


def test_gnnview(ds):
    view = IndividualGNNFigure(datastore=ds)
    df = view.data
    assert df.shape == (42, 6)
    view.datastore.individuals_table.toggle_sample_set(0)
    df = view.data
    assert df.shape == (30, 5)


def test_mean_gnn_view(ds):
    view = MeanGNNFigure(datastore=ds)
    df = view.data
    assert df.shape == (6, 6)
    view = MeanGNNFigure(datastore=ds, zscore=False)
    df = view.data
    assert df.shape == (6, 6)
