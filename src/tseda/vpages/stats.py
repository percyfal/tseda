"""Population genetic statistics.

TODO:
- add more stats
- add generic stats class and let oneway and multiway inherit from it
- add xwheel zoom and pan
- catch error / alert when using mode="branch" on uncalibrated trees
- box plots
"""

import ast

import holoviews as hv
import pandas as pd
import panel as pn
import param
from holoviews.plotting.util import process_cmap

from tseda import config

from .core import View, make_windows

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_width")


# TODO: make sure this is safe
def eval_sample_sets(sample_sets):
    """Evaluate sample sets parameter."""
    return ast.literal_eval(sample_sets)


def eval_indexes(indexes):
    """Evaluate indexes parameter."""
    return ast.literal_eval(indexes)


class OnewayStats(View):
    mode = param.Selector(
        objects=["branch", "site"],
        default="site",
        doc="Select mode for statistics.",
    )
    statistic = param.Selector(
        objects=["Tajimas_D", "diversity"],
        default="diversity",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )
    sample_sets = param.String(
        default="[0,1]",
        doc="Comma-separated list of sample sets (0-indexed) to plot.",
    )

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "Oneway statistical plot. The colors can be modified "
                "in the sample set editor page."
            )
        )

    @param.depends("mode", "statistic", "window_size", "sample_sets")
    def __panel__(self):
        data = None
        windows = make_windows(
            self.window_size, self.datastore.tsm.ts.sequence_length
        )
        sample_sets_list = eval_sample_sets(self.sample_sets)
        try:
            sample_sets = self.datastore.individuals_table.get_sample_sets(
                sample_sets_list
            )
        except KeyError:
            return pn.pane.Alert("Sample set error. Check sample set indexes.")

        if self.statistic == "Tajimas_D":
            data = self.datastore.tsm.ts.Tajimas_D(
                sample_sets, windows=windows, mode=self.mode
            )
        elif self.statistic == "diversity":
            data = self.datastore.tsm.ts.diversity(
                sample_sets, windows=windows, mode=self.mode
            )
        else:
            raise ValueError("Invalid statistic")

        data = pd.DataFrame(
            data,
            columns=[
                self.datastore.sample_sets_table.names[i]
                for i in sample_sets_list
            ],
        )
        position = hv.Dimension(
            "position",
            label="Genome position (bp)",
            range=(0, self.datastore.tsm.ts.sequence_length),
        )
        statistic = hv.Dimension("statistic", label=self.statistic)

        data_dict = {
            ss: hv.Curve((windows, data[ss]), position, statistic).opts(
                color=self.datastore.sample_sets_table.color_by_name[ss]
            )
            for ss in data.columns
        }
        kdims = [hv.Dimension("ss", label="Sample set")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)
        return pn.panel(
            holomap.overlay("ss").opts(legend_position="right"),
            sizing_mode="stretch_width",
        )

    def sidebar(self):
        return pn.Card(
            self.param.mode,
            self.param.statistic,
            self.param.window_size,
            self.param.sample_sets,
            collapsed=False,
            title="Oneway statistics plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class MultiwayStats(View):
    mode = param.Selector(
        objects=["branch", "site"],
        default="site",
        doc="Select mode for statistics.",
    )
    statistic = param.Selector(
        objects=["Fst", "divergence"],
        default="Fst",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )
    sample_sets = param.String(
        default="[0,1,2]",
        doc="Comma-separated list of sample sets (0-indexed) to compare.",
    )
    indexes = param.String(
        default="[(0,1), (0,2), (1,2)]",
        doc=(
            "Comma-separated list of tuples of sample sets "
            "(0-indexed) indexes to compare."
        ),
    )
    cmaps = {
        cm.name: cm
        for cm in hv.plotting.util.list_cmaps(
            records=True, category="Categorical", reverse=False
        )
        if cm.name.startswith("glasbey")
    }
    colormap = param.Selector(
        objects=list(cmaps.keys()),
        default="glasbey_dark",
        doc="Holoviews colormap for sample set pairs",
    )

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "Multiway statistical plot. The colors can be modified "
                "in the colormap dropdown list."
            )
        )

    @pn.depends(
        "mode",
        "statistic",
        "window_size",
        "sample_sets",
        "indexes",
        "colormap",
    )
    def __panel__(self):
        data = None
        tsm = self.datastore.tsm
        sample_sets_list = []
        windows = []
        indexes_list = []
        colormap_list = []
        windows = make_windows(self.window_size, tsm.ts.sequence_length)
        sample_sets_list = eval_sample_sets(self.sample_sets)
        indexes_list = eval_indexes(self.indexes)
        try:
            sample_sets = self.datastore.individuals_table.get_sample_sets(
                sample_sets_list
            )
        except KeyError:
            return pn.pane.Alert("Sample set error. Check sample set indexes.")
        if self.statistic == "Fst":
            data = tsm.ts.Fst(
                sample_sets,
                windows=windows,
                indexes=indexes_list,
                mode=self.mode,
            )
        elif self.statistic == "divergence":
            data = tsm.ts.divergence(
                sample_sets,
                windows=windows,
                indexes=indexes_list,
                mode=self.mode,
            )
        else:
            raise ValueError("Invalid statistic")
        sample_sets_table = self.datastore.sample_sets_table
        data = pd.DataFrame(
            data,
            columns=[
                "-".join(
                    [
                        sample_sets_table.loc(i)["name"],
                        sample_sets_table.loc(j)["name"],
                    ]
                )
                for i, j in indexes_list
            ],
        )
        position = hv.Dimension(
            "position",
            label="Genome position (bp)",
            range=(0, tsm.ts.sequence_length),
        )
        statistic = hv.Dimension("statistic", label=self.statistic)
        cmap = self.cmaps[self.colormap]
        colormap_list = process_cmap(cmap.name, provider=cmap.provider)
        data_dict = {
            sspair: hv.Curve(
                (windows, data[sspair]), position, statistic
            ).opts(color=colormap_list[i])
            for i, sspair in enumerate(data.columns)
        }
        kdims = [hv.Dimension("sspair", label="Sample set combination")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)
        return pn.panel(
            holomap.overlay("sspair").opts(legend_position="right"),
            sizing_mode="stretch_width",
        )

    def sidebar(self):
        return pn.Card(
            self.param.mode,
            self.param.statistic,
            self.param.window_size,
            self.param.sample_sets,
            self.param.indexes,
            self.param.colormap,
            collapsed=False,
            title="Multiway statistics plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class StatsPage(View):
    key = "stats"
    title = "Statistics"
    oneway = param.ClassSelector(class_=OnewayStats)
    multiway = param.ClassSelector(class_=MultiwayStats)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.oneway = OnewayStats(datastore=self.datastore)
        self.multiway = MultiwayStats(datastore=self.datastore)

    def __panel__(self):
        return pn.Column(
            pn.Column(
                self.oneway.tooltip,
                self.oneway,
            ),
            pn.Column(
                self.multiway.tooltip,
                self.multiway,
            ),
        )

    def sidebar(self):
        return pn.Column(
            pn.pane.Markdown("# Statistics"),
            self.oneway.sidebar,
            self.multiway.sidebar,
        )
