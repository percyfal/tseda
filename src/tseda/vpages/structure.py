"""Population structure page.

The page consists of a global GNN analysis and Fst for sample sets
under consideration.

TODO:
- add PCA
- add parameter to subset sample sets of interest
"""

import itertools
from typing import Union

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
    """Makes the GNN plot.

    Attributes:
        warnimng_pane (pn.pane.Alert): A warning message that is activated
        if less than two sample sets are selected.

    Methods:
        __panel__() -> Union[pn.Column, pn.pane.Alert]: Defines the GNN plot.
    """

    warning_pane = pn.pane.Alert(
        """Please select at least 2 samples to visualize this graph.
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
    )

    def __panel__(self) -> Union[pn.Column, pn.pane.Alert]:
        """Returns the GNN cluster plot as a heatmap or a warning message if
        less than 2 samples are selected.

        Returns:
            Union[pn.Column, pn.pane.Alert]: The layout for the GNN cluster
            plot with a descriptive markdown element or a warning message.
        """
        sample_sets = self.datastore.individuals_table.sample_sets()
        samples = [
            sample for sublist in sample_sets.values() for sample in sublist
        ]
        if len(sample_sets) <= 1:
            return self.warning_pane
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
                mean_gnn.hvplot.heatmap(
                    cmap=cc.bgy, height=300, responsive=True
                ),
                pn.pane.Markdown(
                    "**GNN cluster plot** - This heatmap visualizes the "
                    "genealogical relationships between individuals based on "
                    "the proportions of their genealogical nearest neighbors "
                    "(GNN).",
                    sizing_mode="stretch_width",
                ),
                pn.pane.Markdown("FIXME: dendrogram and Z-score\n"),
            )


class Fst(View):
    """Makes the Fst plot.

    Attributes:
        warnimng_pane (pn.pane.Alert): A warning message that is activated
        if less than two sample sets are selected.

    Methods:
        __panel__() -> Union[pn.Column, pn.pane.Alert]: Defines the Fst plot.
    """

    warning_pane = pn.pane.Alert(
        """Please select at least 2 samples to visualize this graph.
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
    )

    def __panel__(self) -> Union[pn.Column, pn.pane.Alert]:
        """Returns the Fst plot as a heatmap or a warning message if less than
        2 samples are selected.

        Returns:
            Union[pn.Column, pn.pane.Alert]: The layout for the Fst
            plot with a descriptive markdown element or a warning message.
        """
        sample_sets = self.datastore.individuals_table.sample_sets()
        if len(sample_sets) <= 1:
            return self.warning_pane
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
                df.hvplot.heatmap(cmap=cc.bgy, height=300, responsive=True),
                pn.pane.Markdown(
                    "**Fst Plot** - Shows the fixation index (Fst) between "
                    "different sample sets, allowing comparison of genetic "
                    "diversity across populations.",
                    sizing_mode="stretch_width",
                ),
            )


class StructurePage(View):
    """Represents the structure page of the tseda application.

    Attributes:
        key (str): A unique identifier for this view within the application.
        title (str): The title displayed on the page.
        gnn (param.ClassSelector): The gnn plot.
        fst (param.ClassSelector): The fst plot.

    Methods:
        __panel__() -> pn.Column: Defines the layout of the main content area.
        sidebar() -> pn.Column: Defines the layout of the sidebar content area.
    """

    key = "structure"
    title = "Structure"
    gnn = param.ClassSelector(class_=GNN)
    fst = param.ClassSelector(class_=Fst)

    def __init__(self, **params):
        super().__init__(**params)
        self.gnn = GNN(datastore=self.datastore)
        self.fst = Fst(datastore=self.datastore)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self) -> pn.Column:
        """Returns the main content of the structure page.

        Returns:
            pn.Column: The layout for the main content area.
        """
        return pn.Column(
            pn.Accordion(
                pn.Column(self.gnn, name="GNN Cluster Plot"),
                pn.Column(self.fst, name="Fst"),
                active=[0, 1],
            )
        )

    def sidebar(self) -> pn.Column:
        """Returns the content of the sidebar.

        Returns:
            pn.Column: The layout for the sidebar.
        """
        return pn.Column(
            pn.pane.HTML(
                "<h2 style='margin: 0;'>Structure</h2>",
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(
                (
                    "This section provides an analysis of the **population "
                    "structure** based on genomic data. "
                    "You can explore two types of plots."
                ),
                sizing_mode="stretch_width",
            ),
            self.sample_sets.sidebar_table,
        )
