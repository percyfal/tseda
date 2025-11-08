"""Population structure page.

The page consists of a global GNN analysis and Fst for sample sets
under consideration.

TODO:
- add PCA
- add parameter to subset sample sets of interest
"""

import holoviews as hv
import hvplot.pandas  # noqa
import panel as pn
import param

from tseda.widgets.structure import (
    FstFigure,
    IndividualGNNFigure,
    MeanGNNFigure,
)

from .core import View

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_width")


class StructurePage(View):
    key = "structure"
    title = "Structure"
    ind_gnn = param.ClassSelector(class_=IndividualGNNFigure)
    mean_gnn = param.ClassSelector(class_=MeanGNNFigure)
    fst = param.ClassSelector(class_=FstFigure)

    def __init__(self, **params):
        super().__init__(**params)
        self.ind_gnn = IndividualGNNFigure(datastore=self.datastore)
        self.mean_gnn = MeanGNNFigure(datastore=self.datastore)
        self.fst = FstFigure(datastore=self.datastore, zscore=False)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self) -> pn.Column:
        """Returns the main content of the structure page.

        Returns:
            pn.Column: The layout for the main content area.
        """
        return pn.Column(
            pn.Accordion(
                pn.Column(self.ind_gnn, name="Individual GNN Plot"),
                pn.Column(self.mean_gnn, name="Mean GNN Plot"),
                pn.Column(self.fst, name="Fst plot"),
                active=[0, 1, 2],
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
                ),
                sizing_mode="stretch_width",
            ),
            self.sample_sets.sidebar_table,
        )
