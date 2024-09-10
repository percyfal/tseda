"""Population genetic statistics.

TODO:
- add more stats
- add generic stats class and let oneway and multiway inherit from it
- add xwheel zoom and pan
- catch error / alert when using mode="branch" on uncalibrated trees
- multiway plot: self.data should not return data but set self._data
  to avoid recalculation of stats when colormap is updated (change
  data function for oneway for consistency)

"""

import ast

import holoviews as hv
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import panel as pn
import param
from holoviews.plotting.util import process_cmap

hv.extension("bokeh")

pn.extension()

palette = list(mcolors.CSS4_COLORS.keys())


# TODO: make sure this is safe
def eval_sample_sets(sample_sets):
    """Evaluate sample sets parameter."""
    return ast.literal_eval(sample_sets)


def eval_indexes(indexes):
    """Evaluate indexes parameter."""
    return ast.literal_eval(indexes)


def make_windows(window_size, sequence_length):
    """Make windows for statistics."""
    num_windows = int(sequence_length / window_size)
    windows = np.linspace(0, sequence_length, num_windows + 1)
    windows[-1] = sequence_length
    return windows


class OnewayStats(param.Parameterized):
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

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.sample_sets_list = []
        self.windows = []

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "Oneway statistical plot. The colors can be modified "
                "in the sample set editor page."
            )
        )

    @property
    @param.depends("statistic", "window_size", "sample_sets")
    def data(self):
        self.windows = make_windows(
            self.window_size, self.tsm.ts.sequence_length
        )
        self.sample_sets_list = eval_sample_sets(self.sample_sets)
        sample_sets = self.tsm.get_sample_sets(self.sample_sets_list)

        if self.statistic == "Tajimas_D":
            return self.tsm.ts.Tajimas_D(
                sample_sets, windows=self.windows, mode=self.mode
            )
        elif self.statistic == "diversity":
            return self.tsm.ts.diversity(
                sample_sets, windows=self.windows, mode=self.mode
            )
        else:
            raise ValueError("Invalid statistic")

    def panel(self):
        data = pd.DataFrame(
            self.data,
            columns=[
                self.tsm.sample_sets[i].name for i in self.sample_sets_list
            ],
        )
        position = hv.Dimension(
            "position",
            label="Genome position (bp)",
            range=(0, self.tsm.ts.sequence_length),
        )
        statistic = hv.Dimension("statistic", label=self.statistic)

        data_dict = {
            ss: hv.Curve((self.windows, data[ss]), position, statistic).opts(
                color=self.tsm.get_sample_set_by_name(ss).color
            )
            for ss in data.columns
        }
        kdims = [hv.Dimension("ss", label="Sample set")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)
        return holomap.overlay("ss").opts(legend_position="right")


class MultiwayStats(param.Parameterized):
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

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.sample_sets_list = []
        self.windows = []
        self.indexes_list = []
        self.colormap_list = []

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "Multiway statistical plot. The colors can be modified "
                "in the colormap dropdown list."
            )
        )

    @property
    @param.depends(
        "statistic",
        "window_size",
        "sample_sets",
        "indexes",
    )
    def data(self):
        self.windows = make_windows(
            self.window_size, self.tsm.ts.sequence_length
        )
        self.sample_sets_list = eval_sample_sets(self.sample_sets)
        self.indexes_list = eval_indexes(self.indexes)
        sample_sets = self.tsm.get_sample_sets(self.sample_sets_list)
        if self.statistic == "Fst":
            return self.tsm.ts.Fst(
                sample_sets,
                windows=self.windows,
                indexes=self.indexes_list,
                mode=self.mode,
            )
        elif self.statistic == "divergence":
            return self.tsm.ts.divergence(
                sample_sets,
                windows=self.windows,
                indexes=self.indexes_list,
                mode=self.mode,
            )
        else:
            raise ValueError("Invalid statistic")

    @param.depends("colormap")
    def panel(self):
        data = pd.DataFrame(
            self.data,
            columns=[
                "-".join(
                    [
                        self.tsm.sample_sets[i].name,
                        self.tsm.sample_sets[j].name,
                    ]
                )
                for i, j in self.indexes_list
            ],
        )
        position = hv.Dimension(
            "position",
            label="Genome position (bp)",
            range=(0, self.tsm.ts.sequence_length),
        )
        statistic = hv.Dimension("statistic", label=self.statistic)
        cmap = self.cmaps[self.colormap]
        colormap_list = process_cmap(cmap.name, provider=cmap.provider)
        data_dict = {
            sspair: hv.Curve(
                (self.windows, data[sspair]), position, statistic
            ).opts(color=colormap_list[i])
            for i, sspair in enumerate(data.columns)
        }
        kdims = [hv.Dimension("sspair", label="Sample set combination")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)
        return holomap.overlay("sspair").opts(legend_position="right")


def page(tsm):
    # TODO: Make it possible to view more than one statistic at a time?
    oneway = OnewayStats(tsm)
    multiway = MultiwayStats(tsm)

    return pn.Column(
        pn.Row(
            pn.Param(oneway.param, width=200),
            pn.Column(
                oneway.tooltip,
                oneway.panel,
            ),
        ),
        pn.Row(
            pn.Param(multiway.param, width=200),
            pn.Column(
                multiway.tooltip,
                multiway.panel,
            ),
        ),
    )
