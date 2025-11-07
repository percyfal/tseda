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


# TODO: make sure this is safe
def eval_comparisons(comparisons):
    """Evaluate comparisons parameter."""
    evaluated = ast.literal_eval(str(comparisons).replace(" & ", ","))
    return [tuple(map(int, item.split(","))) for item in evaluated]


class BaseStats(WindowedFigure):
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
    _min_sample_sets = 1
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

    def __init__(self, **params: Any):
        super().__init__(**params)
        if self.datastore.tsm.is_calibrated:
            self.param.mode.objects = ["site", "branch"]

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
    def sample_select_warning(self) -> pn.pane.Alert:
        return pn.pane.Alert(
            (
                f"Select at least {self._min_sample_sets} sample set to see"
                " this plot. Sample sets are selected on the Individuals page"
            ),
            alert_type="warning",
        )

    @property
    def columns(self) -> List[str]:
        return self.datastore.sample_sets_names

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
        )


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
        if self.datastore.n_sample_sets_ids < 1:
            return self.sample_select_warning
        if self.statistic not in self._fig_text:
            raise ValueError("Invalid statistic")
        data = self.data()
        data_dict = {
            ss: hv.Curve(
                (self.make_windows(), data[ss]),
                self.position,
                self.statistic_dim,
            ).opts(color=self.datastore.sample_sets_table.color_by_name[ss])
            for ss in data.columns
        }
        kdims = [hv.Dimension("ss", label="Sample set")]
        holomap = hv.HoloMap(data_dict, kdims=kdims)
        return pn.Column(
            pn.panel(
                holomap.overlay("ss").opts(legend_position="right"),
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(self._fig_text[self.statistic]),
        )


class MultiwayStats(BaseStats):
    """Oneway statistics base figure

    Create a base figure for oneway statistics plots.

    Attributes:


    """

    _min_sample_sets = 2
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

    @pn.depends(
        "mode", "statistic", "window_size", "colormap", "comparisons.value"
    )
    def __panel__(self):
        """Returns the multiway plot.

        Returns:
            pn.Column: The layout for the main content area.
        """
        self.set_multichoice_options()
        if self.datastore.n_sample_sets_ids < 1:
            return self.sample_select_warning
        if self.comparisons.value == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        if self.indexes == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        if self.statistic not in self._fig_text:
            raise ValueError("Invalid statistic")

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
        return pn.Column(
            pn.panel(
                holomap.overlay("sspair").opts(legend_position="right"),
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(self._fig_text[self.statistic]),
        )


__all__ = (
    "OnewayStats",
    "MultiwayStats",
)
