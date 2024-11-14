"""Genealogical Nearest Neighbors (GNN) analysis.

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

from tseda import config

from .core import View, make_windows
from .map import GeoMap
from .sample_sets import SampleSetsEditor

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_both")


class GNNHaplotype(View):
    """Make GNN haplotype plot."""

    individual_id = param.Integer(
        default=None,
        bounds=(0, None),
        doc="Individual ID (0-indexed)",
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )

    def plot(self, haplotype=0):
        if self.individual_id is None:
            return
        if self.window_size is not None:
            windows = make_windows(
                self.window_size, self.datastore.tsm.ts.sequence_length
            )
        else:
            windows = None
        data = self.datastore.haplotype_gnn(
            self.individual_id, windows=windows
        )
        df = data.loc[data.index.get_level_values("haplotype") == haplotype]
        df = df.droplevel(["haplotype", "end"])
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
            min_width=800,
            min_height=300,
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
        )
        return p

    @pn.depends("individual_id", "window_size")
    def __panel__(self, **params):
        inds = self.datastore.individuals_table.data.rx.value
        if self.individual_id is None:
            return pn.pane.Markdown("")
        nodes = inds.loc[self.individual_id].nodes
        return pn.Column(
            pn.pane.Markdown(f"## Individual id {self.individual_id}"),
            pn.pane.Markdown(f"### Haplotype 0 (sample id {nodes[0]})"),
            self.plot(0),
            pn.pane.Markdown(f"### Haplotype 1 (sample id {nodes[1]})"),
            self.plot(1),
        )

    def sidebar(self):
        return pn.Card(
            self.param.individual_id,
            self.param.window_size,
            collapsed=True,
            title="GNN haplotype options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class VBar(View):
    """Make VBar plot of GNN output."""

    sort_order = param.List(
        default=[],
        item_type=str,
        doc=(
            "Change sort order within sample sets. Default is "
            "to sort by sample index. Provide a list of strings "
            'where items correspond to sample set names, e.g. `["sampleset"]`.'
        ),
    )

    # TODO: move to DataStore class?
    def gnn(self):
        inds = self.datastore.individuals_table.data.rx.value
        samples, sample_sets = self.datastore.individuals_table.sample_sets()
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

    @pn.depends("sort_order")
    def __panel__(self):
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

        if len(self.sort_order) > 0:
            sort_order = (
                ["sample_set_id"] + self.sort_order + ["sample_id", "id"]  # pyright: ignore[reportOperatorIssue]
            )
            df.sort_values(sort_order, axis=0, inplace=True)
            factors = df["x"].values
        source = ColumnDataSource(df)
        fig = figure(
            x_range=FactorRange(
                *factors, group_padding=0.1, subgroup_padding=0
            ),
            height=400,
            sizing_mode="stretch_width",
            tools="xpan,xwheel_zoom,box_select,save,reset",
        )
        fig.add_tools(hover)
        fig.vbar_stack(
            groups,
            source=source,
            x="x",
            color=color,
            legend_label=groups,
            width=1,
            line_color="black",
            line_alpha=0.7,
            line_width=0.5,
            fill_alpha=0.5,
        )

        fig.add_layout(fig.legend[0], "right")
        fig.legend[0].label_text_font_size = "12pt"

        fig.axis.major_tick_line_color = None
        fig.axis.minor_tick_line_color = None
        fig.xaxis.group_label_orientation = 1.0
        fig.xaxis.subgroup_label_orientation = 1.0
        fig.xaxis.group_text_font_size = "14pt"
        fig.xaxis.major_label_orientation = 1.0
        fig.xaxis.major_label_text_font_size = "0pt"
        fig.yaxis.major_label_text_font_size = "12pt"
        fig.yaxis.axis_label_text_font_size = "14pt"
        fig.axis.axis_line_color = None
        fig.grid.grid_line_color = None
        fig.outline_line_color = "black"
        fig.xaxis.separator_line_width = 2.0
        fig.xaxis.separator_line_color = "grey"
        fig.xaxis.separator_line_alpha = 0.5

        return pn.panel(fig)

    def sidebar(self):
        return pn.Card(
            self.param.sort_order,
            collapsed=True,
            title="GNN VBar options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class IGNNPage(View):
    key = "iGNN"
    title = "iGNN"
    geomap = param.ClassSelector(class_=GeoMap)
    vbar = param.ClassSelector(class_=VBar)
    gnnhaplotype = param.ClassSelector(class_=GNNHaplotype)
    sample_sets_editor = param.ClassSelector(class_=SampleSetsEditor)

    def __init__(self, **params):
        super().__init__(**params)
        self.geomap = GeoMap(datastore=self.datastore)
        self.vbar = VBar(datastore=self.datastore)
        self.gnnhaplotype = GNNHaplotype(datastore=self.datastore)
        self.sample_sets_editor = SampleSetsEditor(datastore=self.datastore)

    def __panel__(self):
        return pn.Column(
            pn.Row(
                self.geomap,
            ),
            self.vbar,
            self.gnnhaplotype,
        )

    def sidebar(self):
        return pn.Column(
            self.geomap.sidebar,
            self.gnnhaplotype.sidebar,
            self.vbar.sidebar,
            self.sample_sets_editor.sidebar_table,
        )
