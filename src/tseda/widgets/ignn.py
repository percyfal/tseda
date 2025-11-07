"""Genealogical Nearest Neighbours (GNN) widgets."""

from typing import Any, Union

import holoviews as hv
import hvplot.pandas  # noqa
import pandas as pd
import panel as pn
import param
from bokeh.models import (
    ColumnDataSource,
    FactorRange,
    HoverTool,
)
from bokeh.plotting import figure

from .base import BaseFigure, WindowedFigure


class IGNNHaplotype(WindowedFigure):
    """GNN haplotype base figure.

    Create a GNN haplotype plot for a selected individual.

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
    """

    individual_id = param.Integer(
        default=None,
        doc="Individual ID (0-indexed)",
    )

    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )

    warning_pane = pn.pane.Alert(
        """Please select at least 1 sample to visualize these graphs.
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
        visible=False,
    )

    individual_id_warning = pn.pane.Alert(
        "",
        alert_type="warning",
        visible=False,
    )

    def plot(
        self, haplotype: int = 0
    ) -> Union[hv.core.overlay.NdOverlay, pn.pane.Markdown]:
        if self.individual_id is None:
            return pn.pane.Markdown("Enter a sample ID")
        if self.window_size is not None:
            windows = self.make_windows()
        else:
            windows = None
        data = self.datastore.haplotype_gnn(
            self.individual_id, windows=windows
        )
        df = data.loc[data.index.get_level_values("haplotype") == haplotype]
        df = df.droplevel(["haplotype", "end"])
        if list(df.columns) == []:
            self.warning_pane.visible = True
            return pn.pane.Markdown("")
        else:
            self.warning_pane.visible = False
        populations = [str(x) for x in df.columns]
        colormap = [
            self.datastore.sample_sets_table.color_by_name[x]
            for x in df.columns
        ]
        df.reset_index(inplace=True)
        # TODO: hvplot ignores tools/default_tools parameter
        p = df.hvplot.area(
            x="start",
            y=populations,
            color=colormap,
            legend="right",
            fill_alpha=0.5,
            min_height=self.height,
            responsive=True,
            tools=[
                "pan",
                "xpan",
                "xwheel_zoom",
                "box_select",
                "save",
                "reset",
            ],
        )
        p.opts(
            default_tools=[
                "pan",
                "xpan",
                "xwheel_zoom",
                "box_select",
                "save",
                "reset",
            ],
            active_tools=[
                "pan",
                "xpan",
                "xwheel_zoom",
                "box_select",
                "save",
                "reset",
            ],
            tools=["xpan", "xwheel_zoom", "box_select", "save", "reset"],
            ylabel="Proportion",
        )
        return p

    def plot_haplotype0(
        self,
    ) -> Union[hv.core.overlay.NdOverlay, pn.pane.Markdown]:
        """Creates the GNN Haplotype plot for haplotype 0.

        Returns:
            pn.pane.Markdown: A message directed to the user to enter a valid
            correct sample ID.
            pn.pane.Markdown: A placeholder pane in place to show the
            warningmessage when a incorrect sample ID is entered.
            hv.core.overlay.NdOverlay: A GNN Haplotype plot for haplotype 0.
        """
        return self.plot(0)

    def plot_haplotype1(
        self,
    ) -> Union[hv.core.overlay.NdOverlay, pn.pane.Markdown]:
        """Creates the GNN Haplotype plot for haplotype 1.

        Returns:
            pn.pane.Markdown: A message directed to the user to enter a valid
            correct sample ID.
            pn.pane.Markdown: A placeholder pane in place to show the
            warningmessage when a incorrect sample ID is entered.
            hv.core.overlay.NdOverlay: A GNN Haplotype plot for haplotype 1.
        """
        return self.plot(1)

    def check_inputs(self, inds: pd.core.frame.DataFrame) -> tuple:
        """Checks the inputs to the GNN Haplotype plot.

        Args:
            inds (pandas.core.frame.DataFrame): Contains the data in the
            individuals table.

        Returns:
            pn.pane.Column: If the input argument is valid this coloumn will
            return the nodes of the index and an empty Coloumn. Otherwise it
            will return a None value and a Coloumn telling the user to enter a
            valid sample ID.
        """
        max_id = inds.index.max()
        info_column = pn.Column(
            pn.pane.Markdown(
                "**Enter a valid sample id to see the GNN haplotype plot.**"
            ),
        )
        if self.individual_id is None:
            self.individual_id_warning.visible = False  # No warning for None
            return None, info_column

        try:
            if (
                not isinstance(self.individual_id, (int, float))
                or self.individual_id < 0
            ):
                self.individual_id_warning.object = (
                    "The individual ID does not exist. "
                    f"Valid IDs are in the range 0-{max_id}."
                )
                self.individual_id_warning.visible = True
                return (None, info_column)
            else:
                self.individual_id_warning.visible = False
                nodes = inds.loc[self.individual_id].nodes
                info_column = pn.Column(pn.pane.Markdown(""))
                return (nodes, info_column)
        except KeyError:
            self.individual_id_warning.object = (
                "The individual ID does not exist. "
                f"Valid IDs are in the range 0-{max_id}."
            )
            self.individual_id_warning.visible = True
            return (None, info_column)

    @pn.depends("individual_id", "window_size")
    def __panel__(self, **params) -> pn.Column:
        """Returns the main content for the GNN Haplotype plot which is
        retrieved from the `datastore.tsm.ts` attribute.

        Returns:
            pn.Column: The layout for the main content area of the GNN
            Haplotype plot or a warning message if the input isn't validated.
        """

        inds = self.datastore.individuals_table.data.rx.value
        nodes = self.check_inputs(inds)
        if nodes[0] is not None:
            return pn.Column(
                pn.pane.HTML(
                    "<h2 style='margin: 0;'>"
                    f"- Individual id {self.individual_id}</h2>",
                    sizing_mode="stretch_width",
                ),
                self.warning_pane,
                pn.pane.Markdown(f"### Haplotype 0 (sample id {nodes[0][0]})"),
                self.plot_haplotype0,
                pn.pane.Markdown(f"### Haplotype 1 (sample id {nodes[0][1]})"),
                self.plot_haplotype1,
            )
        else:
            return nodes[1]


class IGNNVBar(BaseFigure):
    """VBar GNN base figure.

    Attributes:
        warning_pane (pn.Alert): a warning panel that is displayed if no
        samples are selected.

    Methods:
        gnn() -> pd.DataFrame: gets the data for the GNN VBar plot.
        __panel__() -> pn.panel: creates the panel containing the GNN VBar
        plot.
        sidebar() -> pn.Card: defines the layout of the sidebar content area
        for the VBar options.
    """

    warning_pane = pn.pane.Alert(
        """Please select at least 1 sample to visualize this graph.
        Sample selection is done on the Individuals page.""",
        alert_type="warning",
    )

    # TODO: move to DataStore class?
    def gnn(self) -> pd.DataFrame:
        """Creates the data for the GNN VBar plot.

        Returns:
            pd.DataFrame: a dataframe containing all the information for the
            GNN VBar plot.
        """
        inds = self.datastore.individuals_table.data.rx.value
        sample_sets = self.datastore.individuals_table.sample_sets()
        samples = [
            sample for sublist in sample_sets.values() for sample in sublist
        ]
        gnn = self.datastore.tsm.ts.genealogical_nearest_neighbours(
            samples, sample_sets=list(sample_sets.values())
        )
        df = pd.DataFrame(
            gnn,
            columns=[i for i in sample_sets],
        )
        samples2ind = [
            self.datastore.individuals_table.sample2ind[i] for i in samples
        ]
        df["id"] = samples2ind
        df["sample_id"] = df.index
        df["sample_set_id"] = [inds.loc[i].sample_set_id for i in samples2ind]
        df.set_index(["sample_set_id", "sample_id", "id"], inplace=True)
        return df

    def _data(self):
        sample_sets = self.datastore.individuals_table.sample_sets()
        if len(list(sample_sets.keys())) < 1:
            return self.warning_pane
        df = self.gnn()
        sample_sets = self.datastore.sample_sets_table.data.rx.value
        inds = self.datastore.individuals_table.data.rx.value
        color = [sample_sets.color[i] for i in df.columns]
        groups = [sample_sets.name[i] for i in df.columns]
        levels = df.index.names
        factors = list(
            tuple([self.datastore.sample_sets_table.names[x[0]], str(x[1])])
            for x in df.index
        )
        df.columns = groups
        df.reset_index(inplace=True)
        df["x"] = factors
        samples2ind = self.datastore.individuals_table.sample2ind
        df["name"] = [inds.loc[samples2ind[x]].name for x in df.index]
        return df, levels, groups, color

    def _hover(self, levels, groups) -> HoverTool:
        hover = HoverTool()
        hover.tooltips = list([("name", "@name")])
        hover.tooltips.extend(list(map(lambda x: (x, f"@{x}"), levels)))
        hover.tooltips.extend(
            list(
                map(
                    lambda x: (x, f"@{x}{{%0.1f}}"),
                    groups,
                )
            )
        )
        return hover

    def _post_process(self, *, df, groups, color) -> pd.DataFrame:
        return df

    def _make_figure(
        self, *, source, groups, color, levels, factors
    ) -> figure:
        fig = figure(
            x_range=FactorRange(
                *factors, group_padding=0.1, subgroup_padding=0
            ),
            height=self.height,
            width=self.width,
            tools="xpan,xwheel_zoom,box_select,save,reset",
            y_axis_label="Proportion",
        )
        hover = self._hover(levels, groups)
        fig.add_tools(hover)
        fig.vbar_stack(
            groups,
            source=source,
            x="x",
            color=color,
            width=1,
            legend_label=groups,
            line_color="black",
            line_alpha=0.7,
            line_width=0.5,
            fill_alpha=0.5,
        )
        if self.sizing_mode is not None:
            fig.sizing_mode = self.sizing_mode
        if self.show_legend:
            fig.add_layout(fig.legend[0], "right")
            fig.legend[0].label_text_font_size = str(self.font_sizes.small)
        else:
            fig.legend.items = []
        fig.axis.major_tick_line_color = None
        fig.axis.minor_tick_line_color = None
        fig.xaxis.group_label_orientation = 1.0
        fig.xaxis.subgroup_label_orientation = 1.0
        fig.xaxis.group_text_font_size = str(self.font_sizes.large)
        fig.xaxis.major_label_orientation = 1.0
        fig.xaxis.major_label_text_font_size = "0pt"
        fig.yaxis.major_label_text_font_size = str(self.font_sizes.normal)
        fig.yaxis.axis_label_text_font_size = str(self.font_sizes.large)
        fig.axis.axis_line_color = None
        fig.grid.grid_line_color = None
        fig.outline_line_color = "black"
        fig.xaxis.separator_line_width = 2.0
        fig.xaxis.separator_line_color = "grey"
        fig.xaxis.separator_line_alpha = 0.5
        return fig

    def __panel__(self) -> Union[pn.pane.plot.Bokeh, pn.pane.Alert, Any]:
        # TODO: Does not accept pn.panel so Any is included as quickfix
        """Returns the main content of the plot which is retrieved from the
        `datastore.tsm.ts` attribute by the gnn() function.

        Returns:
            pn.pane.Alert: a warning pane telling the user that it needs to
            select a sample.
            pn.pane.plot.Bokeh: a panel with the GNN VBar plot.
        """
        df, levels, groups, color = self._data()
        df = self._post_process(df=df, groups=groups, color=color)
        factors = df["x"].values
        source = ColumnDataSource(df)
        fig = self._make_figure(
            source=source,
            groups=groups,
            levels=levels,
            color=color,
            factors=factors,
        )
        return pn.panel(fig)


__all__ = (
    "IGNNHaplotype",
    "IGNNVBar",
)
