"""Population genetic statistics.

TODO:
- add more stats
- add generic stats class and let oneway and multiway inherit from it
- add xwheel zoom and pan
- fix coloring of NdOverlay plots

"""

import ast

import holoviews as hv
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import panel as pn
import param

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
        doc="Comma-separated list of sample sets (0-indexed) to compare.",
    )

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.sample_sets_list = []
        self.windows = []

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
        data_dict = {ss: hv.Curve(data[ss]) for ss in data.columns}
        return pn.pane.HoloViews(
            hv.NdOverlay(data_dict, kdims="sample set"),
            sizing_mode="stretch_width",
        )


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

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.sample_sets_list = []
        self.windows = []
        self.indexes_list = []

    @property
    @param.depends("statistic", "window_size", "sample_sets", "indexes")
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
        data_dict = {sspair: hv.Curve(data[sspair]) for sspair in data.columns}
        return pn.pane.HoloViews(
            hv.NdOverlay(data_dict, kdims="sample set combination"),
            sizing_mode="stretch_width",
        )
        return pn.pane.HoloViews(
            hv.Curve(self.data), sizing_mode="stretch_width"
        )


def page(tsm):
    # TODO: Make it possible to view more than one statistic at a time
    oneway = OnewayStats(tsm)
    multiway = MultiwayStats(tsm)

    return pn.Column(
        oneway.param,
        oneway.panel,
        multiway.param,
        multiway.panel,
    )
