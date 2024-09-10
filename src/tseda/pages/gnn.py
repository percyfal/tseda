"""Genealogical Nearest Neighbors (GNN) analysis.

Draw GNN plots for individuals and haplotypes. The GNN plot shows the
GNN proportions in each sample set for each individual or haplotype.
The GNN proportions are calculated using the genealogical nearest
neighbors method.

Individuals are grouped and colored by sample set. The groupings and
colors can be modified in the sample set editor. Hovering over the bars
in the plot shows the GNN proportions of each sample set for a given
sample.

"""

import hvplot.pandas  # noqa
import panel as pn
import holoviews as hv
from bokeh.plotting import figure
from bokeh.models import (
    FactorRange,
    ColumnDataSource,
    HoverTool,
)
from .map import GeoMap
import param

hv.extension("bokeh")


class VBar(param.Parameterized):
    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self._data = self.tsm.gnn()
        self._color = [
            self.tsm.sample_sets[i].color for i in self._data.columns
        ]
        self._groups = [
            self.tsm.sample_sets[i].name for i in self._data.columns
        ]
        self._levels = self._data.index.names
        self._factors = list(
            tuple([tsm.sample_sets[x[0]].name, str(x[1])])
            for x in self._data.index
        )
        self._data.columns = self.groups
        self._data.reset_index(inplace=True)
        self._data["x"] = self.factors
        self._data["name"] = [
            tsm.individuals[self._data["id"][x]].name for x in self._data.index
        ]

    @property
    def data(self):
        return self._data

    @property
    def color(self):
        """Color mapping for groups"""
        return self._color

    @property
    def groups(self):
        """Group (sample sets) names"""
        return self._groups

    @property
    def levels(self):
        """Sample index levels"""
        return self._levels

    @property
    def factors(self):
        """Factors consist of 2-tuples that correspond to
        (individual, population) grouping"""
        return self._factors

    def plot(self):
        """Make vbar plot. Holoviews does not support grouping by default
        so we need to implement it using low-level bokeh API."""
        hover = HoverTool()
        hover.tooltips = list(
            map(lambda x: (x[0], f"@{x[1]}"), zip(self.levels, self.levels))
        )
        hover.tooltips.extend(
            list(
                map(
                    lambda x: (x[0], f"@{x[1]}{{%0.1f}}"),
                    zip(self.groups, self.groups),
                )
            )
        )

        self._fig = figure(
            x_range=FactorRange(
                *self.factors, group_padding=0.1, subgroup_padding=0
            ),
            height=400,
            sizing_mode="stretch_width",
            tools="xpan,xwheel_zoom,box_select,save,reset",
        )
        self._fig.add_tools(hover)

        source = ColumnDataSource(self.data)
        self._fig.vbar_stack(
            self.groups,
            source=source,
            x="x",
            color=self.color,
            legend_label=self.groups,
            width=1,
            line_color="black",
            line_alpha=0.7,
            line_width=0.5,
            fill_alpha=0.5,
        )

        self._fig.add_layout(self._fig.legend[0], "right")
        self._fig.legend[0].label_text_font_size = "12pt"

        self._fig.axis.major_tick_line_color = None
        self._fig.axis.minor_tick_line_color = None
        self._fig.xaxis.group_label_orientation = 1.0
        self._fig.xaxis.subgroup_label_orientation = 1.0
        self._fig.xaxis.group_text_font_size = "14pt"
        self._fig.xaxis.major_label_orientation = 1.0
        self._fig.xaxis.major_label_text_font_size = "0pt"
        self._fig.yaxis.major_label_text_font_size = "12pt"
        self._fig.yaxis.axis_label_text_font_size = "14pt"
        self._fig.axis.axis_line_color = None
        self._fig.grid.grid_line_color = None
        self._fig.outline_line_color = "black"
        self._fig.xaxis.separator_line_width = 0.0

        return self._fig


def page(tsm):
    geomap = GeoMap(tsm)
    vbar = VBar(tsm)

    layout = pn.Column(
        pn.Row(
            pn.Param(geomap.param, width=200),
            geomap.plot,
        ),
        vbar.plot,
    )

    return layout
