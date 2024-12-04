"""Population structure page.

The page consists of a global GNN analysis and Fst for sample sets
under consideration.

TODO:
- add PCA
- add parameter to subset sample sets of interest

"""

import itertools

import colorcet as cc
import holoviews as hv
import hvplot.pandas  # noqa
import numpy as np
import pandas as pd
import panel as pn
import param

from .core import View

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_width")


class GNN(View):
    """Make aggregated GNN plot."""

    warning_pane = pn.pane.Alert(
        """Please select at least 2 samples to visualize this graph. 
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
    )

    def __panel__(self):
        samples, sample_sets = self.datastore.individuals_table.sample_sets()
        if len(sample_sets) <= 1:
            return pn.Column(
                pn.pane.Markdown("## GNN cluster plot\n"), self.warning_pane
            )
        else:
            sstable = self.datastore.sample_sets_table.data.rx.value
            inds = self.datastore.individuals_table.data.rx.value
            samples2ind = [
                self.datastore.individuals_table.sample2ind[i] for i in samples
            ]

            ts = self.datastore.tsm.ts
            data = ts.genealogical_nearest_neighbours(
                samples, sample_sets=list(sample_sets.values())
            )
            df = pd.DataFrame(
                data,
                columns=[sstable.loc[i]["name"] for i in sample_sets],
            )
            df["focal_population"] = [
                sstable.loc[inds.loc[i].sample_set_id]["name"]
                for i in samples2ind
            ]
            mean_gnn = df.groupby("focal_population").mean()
            # Z-score normalization here!
            return pn.Column(
                pn.pane.Markdown("## GNN cluster plot\n"),
                mean_gnn.hvplot.heatmap(
                    cmap=cc.bgy, height=300, responsive=True
                ),
                pn.pane.Markdown("FIXME: dendrogram and Z-score\n"),
            )


class Fst(View):
    """Make Fst plot."""

    warning_pane = pn.pane.Alert(
        """Please select at least 2 samples to visualize this graph. 
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
    )

    def __panel__(self):
        samples, sample_sets = self.datastore.individuals_table.sample_sets()
        if len(sample_sets) <= 1:
            return pn.Column(pn.pane.Markdown("## Fst\n"), self.warning_pane)
        else:
            sstable = self.datastore.sample_sets_table.data.rx.value
            ts = self.datastore.tsm.ts
            k = len(sample_sets)
            i = list(itertools.product(list(range(k)), list(range(k))))
            groups = [sstable.loc[i]["name"] for i in sample_sets]
            fst = ts.Fst(list(sample_sets.values()), indexes=i)
            df = pd.DataFrame(
                np.reshape(fst, newshape=(k, k)), columns=groups, index=groups
            )
            return pn.Column(
                pn.pane.Markdown("## Fst\n"),
                df.hvplot.heatmap(cmap=cc.bgy, height=300, responsive=True),
            )


class StructurePage(View):
    """Make structure page."""

    key = "structure"
    title = "Structure"
    gnn = param.ClassSelector(class_=GNN)
    fst = param.ClassSelector(class_=Fst)

    def __init__(self, **params):
        super().__init__(**params)
        self.gnn = GNN(datastore=self.datastore)
        self.fst = Fst(datastore=self.datastore)

    def __panel__(self):
        return pn.Column(
            self.gnn,
            self.fst,
        )
