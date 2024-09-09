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

hv.extension("bokeh")


def setup_vbar_data(tsm):
    data = tsm.gnn()
    color = [tsm.sample_sets[i].color for i in data.columns]
    groups = [tsm.sample_sets[i].name for i in data.columns]
    data.columns = groups

    levels = data.index.names
    factors = list(
        tuple([tsm.sample_sets[x[0]].name, str(x[1])]) for x in data.index
    )
    data.reset_index(inplace=True)
    data["x"] = factors
    data["name"] = [tsm.individuals[data["id"][x]].name for x in data.index]
    return data, levels, groups, color, factors


def vbar(source, levels, groups, color, factors):
    """Make vbar plot. Holoviews does not support grouping by default
    so we need to implement it using low-level bokeh API."""
    # Bars plot
    # source = ColumnDataSource(data)
    # factors = data["x"]
    hover = HoverTool()
    hover.tooltips = list(
        map(lambda x: (x[0], f"@{x[1]}"), zip(levels, levels))
    )
    hover.tooltips.extend(
        list(map(lambda x: (x[0], f"@{x[1]}{{%0.1f}}"), zip(groups, groups)))
    )

    bars = figure(
        x_range=FactorRange(*factors, group_padding=0.1, subgroup_padding=0),
        height=400,
        sizing_mode="stretch_width",
        tools="xpan,xwheel_zoom,box_select,save,reset",
    )
    bars.add_tools(hover)

    bars.vbar_stack(
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

    bars.add_layout(bars.legend[0], "right")
    bars.legend[0].label_text_font_size = "12pt"

    bars.axis.major_tick_line_color = None
    bars.axis.minor_tick_line_color = None
    bars.xaxis.group_label_orientation = 1.0
    bars.xaxis.subgroup_label_orientation = 1.0
    bars.xaxis.group_text_font_size = "14pt"
    bars.xaxis.major_label_orientation = 1.0
    bars.xaxis.major_label_text_font_size = "0pt"
    bars.yaxis.major_label_text_font_size = "12pt"
    bars.yaxis.axis_label_text_font_size = "14pt"
    bars.axis.axis_line_color = None
    bars.grid.grid_line_color = None
    bars.outline_line_color = "black"
    bars.xaxis.separator_line_width = 0.0
    return bars


def page(tsm):
    geomap = GeoMap(tsm)
    bars_df, levels, groups, color, factors = setup_vbar_data(tsm)

    bars_df_source = ColumnDataSource(bars_df)
    bars = vbar(bars_df_source, levels, groups, color, factors)

    # bars_df_source.selected.on_change("indices", callback)
    # selection = hv.streams.Selection1D(source=[])

    # def callback(attr, old, new):
    #     selection.source = new

    # def dynamic_map(index):
    #     selected_df = geomap_df.iloc[index]
    #     return selected_df

    # dmap = hv.DynamicMap(dynamic_map, streams=[selection])

    pn.bind(geomap.plot, bars_df_source)

    return pn.Column(geomap.param, geomap.plot, bars)
