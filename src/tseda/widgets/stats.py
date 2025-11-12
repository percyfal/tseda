import ast
import itertools
from typing import Any, Dict, List

import holoviews as hv
import hvplot.pandas  # noqa
import pandas as pd
import panel as pn
import param
from holoviews.plotting.util import process_cmap

from .base import WindowedFigure
from .mixins import SampleSelectWarningMixin


# TODO: make sure this is safe
def eval_comparisons(comparisons):
    """Evaluate comparisons parameter."""
    evaluated = ast.literal_eval(str(comparisons).replace(" & ", ","))
    return [tuple(map(int, item.split(","))) for item in evaluated]


class BaseStats(WindowedFigure, SampleSelectWarningMixin):
    """Base class for statistics figures

    Attributes:
        mode (param.Selector):
            A parameter to select the calculation mode ("site" or "branch").
            Branch mode is only available for calibrated data.
        statistic (param.Selector):
            A parameter to select the statistic to calculate
            (e.g., "Tajimas_D", "diversity").
            Names correspond to tskit method names.
        sample_select_warning (pn.pane.Alert):
            An alert panel displayed when no sample sets are selected.

    Methods:
        __panel__() -> pn.Column:
            Generates the plot containing the statistics plot.
            Raises a warning if no sample sets are selected.
    """

    _fig_text = {}
    mode = param.Selector(
        objects=["site"],
        default="site",
        doc="""Select mode (site or branch) for statistics.
        Branch mode is only available for calibrated data.""",
    )
    statistic = param.Selector(
        objects=[],
        default=None,
        doc="""Select statistic to plot.""",
    )

    def __init__(self, caption: bool = False, **params: Any):
        super().__init__(**params)
        if self.datastore.tsm.is_calibrated:
            self.param.mode.objects = ["site", "branch"]
        self._caption = caption

    @property
    def columns(self) -> List[str]:
        return self.datastore.sample_sets_names

    @property
    def colormap(self) -> Dict:
        return self.datastore.sample_sets_table.color_by_name

    @property
    def data(self):
        if self.statistic is None:
            return
        kw = {}
        if hasattr(self, "indexes"):
            kw = {"indexes": self.indexes}
        fun = getattr(self.datastore.tsm.ts, self.statistic)
        data = fun(
            self.datastore.sample_sets_individuals,
            windows=self.make_windows(),
            mode=self.mode,
            **kw,
        )
        return pd.DataFrame(
            data,
            columns=self.columns,
        )


class BaseHoloviewsStats(BaseStats):
    """Base class for Holoviews-based figures.

    Holoviews figures take Dataset or data_dict objects as input.
    """

    _plot_mapping = {
        "line": hv.Curve,
        "kde": hv.Distribution,
        "box": hv.BoxWhisker,
        "violin": hv.Violin,
    }
    _boxwhisker = ["box", "violin"]
    _ndoverlay = ["kde"]
    _holomap = ["line"]

    plotfun = param.Selector(
        objects=["line", "kde", "box", "violin"],
        default="line",
        doc="Plotting function.",
    )

    @property
    def position(self):
        return hv.Dimension(
            "position",
            label="Genome position (bp)",
            range=(0, self.datastore.tsm.ts.sequence_length),
        )

    @property
    def statistic_dim(self):
        return hv.Dimension("statistic", label=self.statistic)

    @property
    def kdims(self) -> List[hv.Dimension]:
        return [hv.Dimension(self.dim_key, label=self.dim_label)]

    @property
    def holomap(self) -> hv.HoloMap:
        return hv.HoloMap(self.data_dict, kdims=self.kdims)

    @property
    def ndoverlay(self) -> hv.NdOverlay:
        return hv.NdOverlay(self.data_dict)

    @property
    def boxwhisker(self) -> hv.BoxWhisker:
        return hv.BoxWhisker(
            self.data.melt(var_name=self.dim_label, value_name=self.statistic),
            kdims=[self.dim_label],
            vdims=[self.statistic],
        )

    @property
    def data_dict(self) -> dict:
        plotfun = self._plot_mapping[self.plotfun]
        if self.plotfun in self._holomap:
            data_dict = {
                x: plotfun(
                    (self.make_windows(), self.data[x]),
                    self.position,
                    self.statistic_dim,
                ).opts(color=self.colormap[x])
                for x in self.columns
            }
        elif self.plotfun in self._ndoverlay:
            data_dict = {
                x: plotfun(self.data[x]).opts(color=self.colormap[x])
                for x in self.columns
            }
        return data_dict

    @property
    def plot(self):
        if self.plotfun in self._holomap:
            return self.holomap.overlay(self.dim_key).opts(
                legend_position="top",
                legend_muted=True,
                width=self.width,
                height=self.height,
            )
        elif self.plotfun in self._ndoverlay:
            return self.ndoverlay.opts(
                legend_position="right",
                width=self.width,
                height=self.height,
            )
        elif self.plotfun in self._boxwhisker:
            return self.boxwhisker.opts(
                xrotation=45,
                width=self.width,
                height=self.height,
            )

    @param.depends("mode", "statistic", "window_size")
    def __panel__(self):
        if self.datastore.n_sample_sets_ids < self._min_sample_sets:
            return self.sample_select_warning
        if self.statistic not in self._fig_text:
            raise ValueError("Invalid statistic")
        if self._caption:
            return pn.Column(self.plot, self.caption)
        return self.plot


class OnewayStats(param.Parameterized):
    _min_sample_sets = 1
    statistic = param.Selector(
        objects=["Tajimas_D", "diversity"],
        default="diversity",
        doc="""Select statistic to plot.""",
    )
    _fig_text = {
        "diversity": "**Oneway Diversity plot** - Lorem Ipsum",
        "Tajimas_D": "**Oneway Tajimas_D plot** - Lorem Ipsum",
    }
    dim_key = "ss"
    dim_label = "Sample set"


class OnewayHoloviewsStats(OnewayStats, BaseHoloviewsStats):
    """Oneway statistics base figure

    Create a base figure for oneway statistics plots.

    Attributes:


    """


class BaseHvplotStats(BaseStats):
    def kde(self):
        return self.data.hvplot.kde(cmap=self.colormap)

    def boxplot(self):
        return self.data.hvplot.box(rot=45, cmap=self.colormap)


class OnewayHvplotStats(OnewayStats, BaseHvplotStats):
    """Oneway Hvplot statistics widget"""


class MultiwayStats(param.Parameterized):
    _min_sample_sets = 2
    statistic = param.Selector(
        objects=["Fst", "divergence"],
        default="Fst",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    _fig_text = {
        "Fst": "**Multiway Fst plot** - Lorem Ipsum",
        "divergence": "**Multiway divergence plot** - Lorem Ipsum",
    }
    dim_key = "sspair"
    dim_label = "Sample set pair"


class MultiwayHoloviewsStats(MultiwayStats, BaseHoloviewsStats):
    """Multiway Holoviews statistics"""

    comparisons = pn.widgets.MultiChoice(
        name="Comparisons", description="Choose indexes to compare.", value=[]
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

    def set_multichoice_options(self):
        """This method dynamically populates the `comparisons` widget with a
        list of possible sample set pairs based on the currently selected
        sample sets in the `individuals_table`."""
        all_comparisons = list(
            f"{x} & {y}"
            for x, y in itertools.combinations(
                list(self.datastore.sample_sets_ids),
                2,
            )
        )
        self.comparisons.options = all_comparisons

    @property
    def columns(self) -> List[str]:
        sample_sets_table = self.datastore.sample_sets_table
        columns = [
            "-".join(
                [
                    sample_sets_table.loc(i)["name"],
                    sample_sets_table.loc(j)["name"],
                ]
            )
            for i, j in self.indexes
        ]
        return columns

    @property
    def indexes(self):
        comparisons = eval_comparisons(self.comparisons.value)
        all_sample_sets = self.datastore.individuals_table.sample_sets(
            only_selected=False
        )
        all_sample_sets_sorted = {
            key: all_sample_sets[key] for key in sorted(all_sample_sets)
        }
        comparisons_indexes = [
            (
                list(all_sample_sets_sorted.keys()).index(x),
                list(all_sample_sets_sorted.keys()).index(y),
            )
            for x, y in comparisons
            if x in all_sample_sets_sorted and y in all_sample_sets_sorted
        ]
        return comparisons_indexes

    @property
    def data_dict(self) -> dict:
        cmap = self.cmaps[self.colormap]
        colormap_list = process_cmap(cmap.name, provider=cmap.provider)
        plotfun = self._plot_mapping[self.plotfun]
        if self.plotfun in self._holomap:
            data_dict = {
                sspair: hv.Curve(
                    (self.make_windows(), self.data[sspair]),
                    self.position,
                    self.statistic_dim,
                ).opts(color=colormap_list[i])
                for i, sspair in enumerate(self.data.columns)
            }
        elif self.plotfun in self._ndoverlay:
            data_dict = {
                sspair: plotfun(self.data[sspair]).opts(color=colormap_list[i])
                for i, sspair in enumerate(self.data.columns)
            }
        return data_dict

    @param.depends("mode", "statistic", "window_size", "comparisons")
    def __panel__(self):
        self.set_multichoice_options()
        if self.comparisons.value == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        if self.indexes == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        return super().__panel__()


__all__ = (
    "OnewayHoloviewsStats",
    "MultiwayHoloviewsStats",
)
