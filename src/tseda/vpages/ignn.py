"""Genealogical Nearest Neighbours (GNN) analysis.

Draw GNN plots for individuals and haplotypes. The GNN plot shows the
GNN proportions in each sample set for each individual or haplotype.
The GNN proportions are calculated using the genealogical nearest
neighbors method.

Individuals are grouped and colored by sample set. The groupings and
colors can be modified in the sample set editor. Hovering over the bars
in the plot shows the GNN proportions of each sample set for a given
sample.

TODO:

- linked brushing between the map and the GNN plot
"""

from typing import Any, Union

import holoviews as hv
import hvplot.pandas  # noqa
import panel as pn
import param

from tseda import config
from tseda.widgets import IGNNHaplotype, IGNNVBar

from .core import View
from .map import GeoMap

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_both")


class GNNHaplotype(IGNNHaplotype):
    """Make GNN haplotype plot. This class creates a Panel object that displays
    a GNN haplotype plot for a selected individual.

    Attributes:
        individual_id (int): the ID of the individual to visualize (0-indexed).
        Defaults to None.
        window_size (int): The size of the window to use for visualization.
        Defaults to 10000. Must be greater than 0.
        warning_pane (pn.Alert): a warning panel that is displayed if no
        samples are selected.
        individual_id_warning (pn.Alert): a warning panel that is displayed
        if an invalid individual ID is entered.

    Methods:
        plot(haplotype=0): makes the haplotype plot.
        plot_haplotype0(): calls the plot function for haplotype 0.
        plot_haplotype1(): calls the plot function for haplotype 1.
        __panel__() -> pn.Column: Defines the layout of the main content area
        or sends out a warning message if the user input isn't valid.
        sidebar() -> pn.Card: Defines the layout of the sidebar content area.
    """

    def sidebar(self) -> pn.Card:
        """Returns the content of the sidbar options for the GNN Haplotype
        plot.

        Returns:
            pn.Card: The layout for the sidebar content area connected to the
            GNN Haplotype plot.
        """
        return pn.Card(
            self.param.individual_id,
            self.param.window_size,
            self.individual_id_warning,
            collapsed=False,
            title="GNN haplotype options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class VBar(IGNNVBar):
    """Make VBar plot of GNN output. This class creates a Panel object that
    displays a VBar plot of the sample sets.

    Attributes:
        sorting (pn.Selector): the selected population to base the sort order
        on.
        sort_order (pn.Selector): the selected sorting order
        (Ascending/Descending)

    Methods:
        gnn() -> pd.DataFrame: gets the data for the GNN VBar plot.
        __panel__() -> pn.panel: creates the panel containing the GNN VBar
        plot.
        sidebar() -> pn.Card: defines the layout of the sidebar content area
        for the VBar options.
    """

    sorting = param.Selector(
        doc="Select what population to base the sort order on. Default is "
        "to sort by sample index",
        allow_None=True,
        default=None,
        label="Sort by",
    )

    sort_order = param.Selector(
        doc="Select the sorting order.",
        objects=["Ascending", "Descending"],
        default="Ascending",
    )

    def _post_process(self, *, df, groups, color):
        if self.sorting is not None and self.sorting != "":
            sort_by = (
                ["sample_set_id"] + [self.sorting] + ["sample_id", "id"]  # pyright: ignore[reportOperatorIssue]
            )
            ascending = [True, False, False, False]

            columns = df.columns.tolist()
            columns.remove(self.sorting)
            id_index = columns.index("id")
            columns.insert(id_index + 1, self.sorting)
            df = df[columns]
            sorting_index = groups.index(self.sorting)
            groups[sorting_index], groups[0] = groups[0], groups[sorting_index]
            color[sorting_index], color[0] = color[0], color[sorting_index]
        else:
            sort_by = ["sample_set_id", "sample_id", "id"]
            ascending = [True, False, False]
        if self.sort_order == "Ascending":
            df.sort_values(sort_by, axis=0, inplace=True)
        else:
            df.sort_values(
                sort_by,
                ascending=ascending,
                axis=0,
                inplace=True,
            )
        return df

    @pn.depends("sorting", "sort_order")
    def __panel__(self) -> Union[pn.pane.plot.Bokeh, pn.pane.Alert, Any]:
        """Return vbar plot panel or warning pane.

        Returns:
            pn.pane.Alert: a warning pane telling the user that it needs to
            select a sample.
            pn.pane.plot.Bokeh: a panel with the GNN VBar plot.
        """
        self.param.sorting.objects = [""] + list(
            self.datastore.sample_sets_table.names.values()
        )
        if self.sizing_mode is None:
            self.sizing_mode = "stretch_width"
        return super().__panel__()

    def sidebar(self):
        """Returns the content of the sidbar options for the VBar plot.

        Returns:
            pn.Card: The layout for the sidebar content area connected to the
            VBar plot.
        """
        return pn.Card(
            self.param.sorting,
            self.param.sort_order,
            collapsed=False,
            title="GNN VBar options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class IGNNPage(View):
    """Make the iGNN page. This class creates the iGNN page.

    Attributes:
        key (str): A unique identifier for the iGNN instance.
        title (str): The display title for the iGNN instance.
        geomap (GeoMap): An instance of the GeoMap class, providing geographic
        visualizations of genomic data.
        vbar (VBar): An instance of the VBar class, providing bar plot
        visualizations of genomic data.
        gnnhaplotype (GNNHaplotype): An instance of the GNNHaplotype class,
        handling GNN-based haplotype analysis.
        sample_sets (pandas.DataFrame): A DataFrame containing information
        about the available sample sets.

    Methods:
        __panel__() -> pn.Column: Defines the layout of the main content area.
        sidebar() -> pn.Column: Defines the layout of the sidebar content area.
    """

    key = "iGNN"
    title = "iGNN"
    geomap = param.ClassSelector(class_=GeoMap)
    vbar = param.ClassSelector(class_=VBar)
    gnnhaplotype = param.ClassSelector(class_=GNNHaplotype)

    def __init__(self, **params):
        super().__init__(**params)
        self.geomap = GeoMap(datastore=self.datastore)
        self.vbar = VBar(datastore=self.datastore)
        self.gnnhaplotype = GNNHaplotype(datastore=self.datastore)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self) -> pn.Column:
        """Returns the main content of the page which is retrieved from the
        `datastore.tsm.ts` attribute.

        Returns:
            pn.Column: The layout for the main content area.
        """

        return pn.Column(
            pn.Accordion(
                pn.Column(
                    pn.Column(self.geomap, sizing_mode="scale_both"),
                    pn.pane.Markdown(
                        "**Map** - Displays the geographical locations "
                        "where samples were collected and visually "
                        "represents their group sample affiliations "
                        "through colors.",
                        sizing_mode="stretch_both",
                    ),
                    name="Geomap",
                    min_width=400,
                    min_height=600,
                    sizing_mode="stretch_both",
                ),
                pn.Column(
                    self.vbar,
                    pn.pane.Markdown(
                        "**vBar** - Lorem ipsum",
                        sizing_mode="stretch_width",
                    ),
                    name="VBar Plot",
                ),
                pn.Column(
                    self.gnnhaplotype,
                    name="GNN Haplotype Plot",
                    sizing_mode="stretch_both",
                    min_height=600,
                ),
                active=[0, 1, 2],
            ),
            pn.Spacer(sizing_mode="stretch_both", max_height=5),
        )

    def sidebar(self) -> pn.Column:
        """Returns the sidebar content of the page which is retrieved from the
        `datastore.tsm.ts` attribute.

        Returns:
           pn.Column: The layout for the sidebar content area.
        """

        return pn.Column(
            pn.pane.HTML(
                "<h2 style='margin: 0;'>iGNN</h2>", sizing_mode="stretch_width"
            ),
            pn.pane.Markdown(
                (
                    "This section provides interactive visualizations for "
                    "**Genealogical Nearest Neighbors "
                    "(GNN)** analysis.<br><br>"
                    "Use the controls below to customize the plots and "
                    "adjust parameters."
                ),
                sizing_mode="stretch_width",
            ),
            self.geomap.sidebar,
            self.vbar.sidebar,
            self.gnnhaplotype.sidebar,
            self.sample_sets.sidebar_table,
        )
