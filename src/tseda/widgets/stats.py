import ast
import itertools
from typing import Any, List, Union

import holoviews as hv
import hvplot.pandas  # noqa
import pandas as pd
import panel as pn
import param
from holoviews.plotting.util import process_cmap

from .base import WindowedFigure
from .mixins import MultiSampleSelectWarningMixin, SampleSelectWarningMixin


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
    dim_key = "ss"
    dim_label = "Sample set"
    _plotfun = "Curve"

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
    def plotfun(self):
        return getattr(hv, self._plotfun)

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
    def columns(self) -> List[str]:
        return self.datastore.sample_sets_names

    @property
    def kdims(self) -> List[hv.Dimension]:
        return [hv.Dimension(self.dim_key, label=self.dim_label)]

    @property
    def holomap(self) -> hv.HoloMap:
        return hv.HoloMap(self.data_dict, kdims=self.kdims)

    @property
    def data_dict(self) -> dict:
        data = self.data()
        data_dict = {
            x: self.plotfun(
                (self.make_windows(), data[x]),
                self.position,
                self.statistic_dim,
            ).opts(color=self.datastore.sample_sets_table.color_by_name[x])
            for x in data.columns
        }
        return data_dict

    def data(self, **kw):
        if self.statistic is None:
            return
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
        ).copy()

    def kde(self):
        return self.data().hvplot.kde()

    def boxplot(self):
        return self.data().hvplot.box(rot=45)

    # FIXME: Several types of plots that require different dimensions
    # (holoviews)
    @property
    def plot(self) -> pn.panel:
        gspec = pn.GridSpec(ncols=2, nrows=3, sizing_mode="stretch_width")
        gspec[0, :] = self.holomap.overlay(self.dim_key).opts(
            legend_position="top", legend_muted=True
        )
        gspec[1:3, 0] = self.boxplot().opts(height=int(self.height * 1.5))
        gspec[1:3, 1] = self.kde().opts(height=int(self.height * 1.5))
        return gspec

    @property
    def caption(self):
        return self._fig_text[self.statistic]

    def __panel__(self) -> Union[pn.panel, pn.Column, pn.pane.Alert]:
        if self.datastore.n_sample_sets_ids < self._min_sample_sets:
            return self.sample_select_warning
        if self.statistic not in self._fig_text:
            raise ValueError("Invalid statistic")
        if self._caption:
            return pn.Column(self.plot, self.caption)
        return self.plot


class OnewayStats(BaseStats):
    """Oneway statistics base figure

    Create a base figure for oneway statistics plots.

    Attributes:


    """

    statistic = param.Selector(
        objects=["Tajimas_D", "diversity"],
        default="diversity",
        doc="""Select statistic to plot.""",
    )
    _fig_text = {
        "diversity": "**Oneway Diversity plot** - Lorem Ipsum",
        "Tajimas_D": "**Oneway Tajimas_D plot** - Lorem Ipsum",
    }

    @param.depends("mode", "statistic", "window_size")
    def __panel__(self) -> Union[pn.Column, pn.pane.Alert]:
        """Generates the plot containing the oneway statistics plot.

        Returns:
            Union[pn.Column, pn.pane.Alert]: The Panel object containing the
            oneway statistics plot or a warning message if no sample sets are
            selected.
        """
        return super().__panel__()


class MultiwayStats(BaseStats, MultiSampleSelectWarningMixin):
    """Multiway statistics base figure

    Create a base figure for multiway statistics plots.

    Attributes:


    """

    _fig_text = {
        "Fst": "**Multiway Fst plot** - Lorem Ipsum",
        "divergence": "**Multiway divergence plot** - Lorem Ipsum",
    }

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
    statistic = param.Selector(
        objects=["Fst", "divergence"],
        default="Fst",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    dim_key = "sspair"

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
        data = self.data(indexes=self.indexes)
        cmap = self.cmaps[self.colormap]
        colormap_list = process_cmap(cmap.name, provider=cmap.provider)
        data_dict = {
            sspair: hv.Curve(
                (self.make_windows(), data[sspair]),
                self.position,
                self.statistic_dim,
            ).opts(color=colormap_list[i])
            for i, sspair in enumerate(data.columns)
        }
        return data_dict

    def kde(self):
        return self.data(indexes=self.indexes).hvplot.kde()

    def boxplot(self):
        return self.data(indexes=self.indexes).hvplot.box(rot=45)

    @property
    def holomap(self) -> hv.HoloMap:
        return hv.HoloMap(
            self.data_dict, kdims=self.kdims, sizing_mode="stretch_width"
        )

    @property
    def plot(self) -> pn.panel:
        gspec = pn.GridSpec(ncols=2, nrows=2, sizing_mode="stretch_both")
        gspec[0, :] = self.holomap.overlay(self.dim_key).opts(
            legend_position="top"
        )
        gspec[1, 0] = self.boxplot()
        gspec[1, 1] = self.kde()
        return gspec

    @pn.depends(
        "mode", "statistic", "window_size", "colormap", "comparisons.value"
    )
    def __panel__(self):
        """Returns the multiway plot.

        Returns:
            pn.Column: The layout for the main content area.
        """
        self.set_multichoice_options()
        if self.datastore.n_sample_sets_ids < self._min_sample_sets:
            return self.sample_select_warning
        if self.statistic not in self._fig_text:
            raise ValueError("Invalid statistic")
        if self.comparisons.value == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        if self.indexes == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        data = self.data(indexes=self.indexes)
        cmap = self.cmaps[self.colormap]
        colormap_list = process_cmap(cmap.name, provider=cmap.provider)
        data_dict = {
            sspair: hv.Curve(
                (self.make_windows(), data[sspair]),
                self.position,
                self.statistic_dim,
            ).opts(color=colormap_list[i])
            for i, sspair in enumerate(data.columns)
        }
        kdims = [hv.Dimension("sspair", label="Sample set combination")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)

        gspec = pn.GridSpec(ncols=2, nrows=3)
        gspec[0, :] = holomap.overlay("sspair").opts(
            legend_position="top", legend_muted=True, width=self.width
        )
        gspec[1:3, 0] = self.boxplot().opts(height=int(self.height * 1.5))
        gspec[1:3, 1] = self.kde().opts(height=int(self.height * 1.5))
        if self._caption:
            return pn.Column(gspec, self.caption)
        return gspec

        # return pn.Column(
        #     pn.panel(
        #         holomap.overlay("sspair").opts(legend_position="right"),
        #         sizing_mode="stretch_width",
        #     ),
        #     pn.pane.Markdown(self._fig_text[self.statistic]),
        # )
        # return self.plot()
        # return self.kde()
        # return pn.Column(
        #     pn.panel(
        #         holomap.overlay("sspair").opts(legend_position="right"),
        #         sizing_mode=self.sizing_mode,
        #     ),
        #     pn.pane.Markdown(self._fig_text[self.statistic]),
        # )


__all__ = (
    "OnewayStats",
    "MultiwayStats",
)
