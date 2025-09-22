"""Population genetic statistics.

TODO:
- add more stats
- add generic stats class and let oneway and multiway inherit from it
- add xwheel zoom and pan
- catch error / alert when using mode="branch" on uncalibrated trees
- box plots
"""

import ast
import itertools
from typing import Union

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
def eval_comparisons(comparisons):
    """Evaluate comparisons parameter."""
    evaluated = ast.literal_eval(str(comparisons).replace(" & ", ","))
    return [tuple(map(int, item.split(","))) for item in evaluated]


def eval_indexes(indexes):
    """Evaluate indexes parameter."""
    return ast.literal_eval(indexes)


class OnewayStats(View):
    """This class defines a view for one-way population genetic statistics
    plots.

    Attributes:
    mode (param.Selector):
        A parameter to select the calculation mode ("site" or "branch").
        Branch mode is only available for calibrated data. (default: "site")
    statistic (param.Selector):
        A parameter to select the statistic to calculate
        (e.g., "Tajimas_D", "diversity").
        Names correspond to tskit method names. (default: "diversity")
    window_size (param.Integer):
        A parameter to define the size of the window for window-based
        statistics.
        (default: 10000, bounds=(1, None))
    sample_select_warning (pn.pane.Alert):
        An alert panel displayed when no sample sets are selected.
    tooltip (pn.widgets.TooltipIcon):
        A tooltip icon providing information about the plot.

    Methods:
    tooltip() -> pn.widgets.TooltipIcon:
            Returns a tooltip for the plot.
    __panel__() -> pn.Column:
        Generates the view containing the one-way statistics plot.
        Raises a warning if no sample sets are selected.
    sidebar() -> pn.Card:
        Creates the sidebar panel with controls for the plot.
    """

    mode = param.Selector(
        objects=["site"],
        default="site",
        doc="""Select mode (site or branch) for statistics.
        Branch mode is only available for calibrated data.""",
    )
    statistic = param.Selector(
        objects=["Tajimas_D", "diversity"],
        default="diversity",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )
    sample_select_warning = pn.pane.Alert(
        """Select at least 1 sample set to see this plot.
        Sample sets are selected on the Individuals page""",
        alert_type="warning",
    )

    @property
    def tooltip(self):
        """Returns a TooltipIcon widget containing information about the oneway
        statistical plot and how to edit it.

        Returns:
            pn.widgets.TooltipIcon: A TooltipIcon widget displaying
            the information.
        """
        return pn.widgets.TooltipIcon(
            value=(
                "Oneway statistical plot. The colors can be modified "
                "in the sample set editor page."
            )
        )

    def __init__(self, **params):
        super().__init__(**params)
        if self.datastore.tsm.ts.time_units != "uncalibrated":
            self.param.mode.objects = ["branch", "site"]

    @param.depends("mode", "statistic", "window_size")
    def __panel__(self) -> Union[pn.Column, pn.pane.Alert]:
        """Returns the plot.

        Returns:
            pn.Column: The layout for the plot.
        """
        data = None
        windows = make_windows(
            self.window_size, self.datastore.tsm.ts.sequence_length
        )
        sample_sets_dictionary = self.datastore.individuals_table.sample_sets()
        sample_sets_ids = list(sample_sets_dictionary.keys())
        if len(sample_sets_ids) < 1:
            return self.sample_select_warning
        sample_sets_individuals = list(sample_sets_dictionary.values())

        if self.statistic == "Tajimas_D":
            data = self.datastore.tsm.ts.Tajimas_D(
                sample_sets_individuals, windows=windows, mode=self.mode
            )
            fig_text = "**Oneway Tajimas_D plot** - Lorem Ipsum"
        elif self.statistic == "diversity":
            data = self.datastore.tsm.ts.diversity(
                sample_sets_individuals, windows=windows, mode=self.mode
            )
            fig_text = "**Oneway Diversity plot** - Lorem Ipsum"
        else:
            raise ValueError("Invalid statistic")

        data = pd.DataFrame(
            data,
            columns=[
                self.datastore.sample_sets_table.names[i]
                for i in sample_sets_ids
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
        return pn.Column(
            pn.panel(
                holomap.overlay("ss").opts(legend_position="right"),
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(fig_text),
        )

    def sidebar(self) -> pn.Card:
        """Returns the content of the sidebar.

        Returns:
            pn.Card: The layout for the sidebar.
        """
        return pn.Card(
            self.param.mode,
            self.param.statistic,
            self.param.window_size,
            collapsed=False,
            title="Oneway statistics plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class MultiwayStats(View):
    """This class defines a view for multi-way population genetic statistics
    plots.

    Attributes:
    mode (param.Selector):
        A parameter to select the calculation mode ("site" or "branch").
        Branch mode is only available for calibrated data. (default: "site")
    statistic (param.Selector):
        A parameter to select the statistic to calculate (e.g., "Fst",
        "divergence").
        Names correspond to tskit method names. (default: "Fst")
    window_size (param.Integer):
        A parameter to define the size of the window for window-based
        statistics.
        (default: 10000, bounds=(1, None))
    comparisons (pn.widgets.MultiChoice):
        A multi-choice widget for selecting sample set pairs to compare.
    sample_select_warning (pn.pane.Alert):
        An alert panel displayed when no sample sets are selected.
    cmaps (dict):
        A dictionary containing available Holoviews colormaps.
    colormap (param.Selector):
        A parameter to select the colormap for the plot.
        (default: "glasbey_dark")

    Methods:
    set_multichoice_options():
        Updates the options for the comparisons multi-choice widget based
        on available sample sets.
    __panel__() -> pn.Column:
        Generates the view containing the multiway statistics plot.
        Raises a warning if no sample sets are selected.
    sidebar() -> pn.Card:
        Creates the sidebar panel with controls for the plot.
    """

    mode = param.Selector(
        objects=["site"],
        default="site",
        doc="""Select mode (site or branch) for statistics.
        Branch mode is only available for calibrated data.""",
    )
    statistic = param.Selector(
        objects=["Fst", "divergence"],
        default="Fst",
        doc="Select statistic. Names correspond to tskit method names.",
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )
    comparisons = pn.widgets.MultiChoice(
        name="Comparisons", description="Choose indexes to compare.", value=[]
    )
    sample_select_warning = pn.pane.Alert(
        """Select at least 2 sample sets to see this plot.
        Sample sets are selected on the Individuals page""",
        alert_type="warning",
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

    def __init__(self, **params):
        super().__init__(**params)
        if self.datastore.tsm.ts.time_units != "uncalibrated":
            self.param.mode.objects = ["branch", "site"]

    @property
    def tooltip(self):
        """Returns a TooltipIcon widget containing information about the
        multiway statistical plot and how to edit it.

        Returns:
            pn.widgets.TooltipIcon: A TooltipIcon widget displaying
            the information.
        """
        return pn.widgets.TooltipIcon(
            value=(
                "Multiway statistical plot. The colors can be modified "
                "in the colormap dropdown list."
            )
        )

    def set_multichoice_options(self):
        """This method dynamically populates the `comparisons` widget with a
        list of possible sample set pairs based on the currently selected
        sample sets in the `individuals_table`."""
        sample_sets = self.datastore.individuals_table.sample_sets()
        all_comparisons = list(
            f"{x} & {y}"
            for x, y in itertools.combinations(
                list(sample_sets.keys()),
                2,
            )
        )
        self.comparisons.options = all_comparisons

    @pn.depends(
        "mode", "statistic", "window_size", "colormap", "comparisons.value"
    )
    def __panel__(self):
        """Returns the multiway plot.

        Returns:
            pn.Column: The layout for the main content area.
        """
        self.set_multichoice_options()

        data = None
        tsm = self.datastore.tsm
        windows = []
        colormap_list = []
        windows = make_windows(self.window_size, tsm.ts.sequence_length)
        comparisons = eval_comparisons(self.comparisons.value)

        selected_sample_sets = self.datastore.individuals_table.sample_sets()
        selected_sample_sets_ids = list(selected_sample_sets.keys())
        if len(selected_sample_sets_ids) < 2:
            return self.sample_select_warning
        elif self.comparisons.value == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        all_sample_sets = self.datastore.individuals_table.sample_sets(
            only_selected=False
        )
        all_sample_sets_sorted = {
            key: all_sample_sets[key] for key in sorted(all_sample_sets)
        }
        sample_sets_individuals = list(all_sample_sets_sorted.values())
        comparisons_indexes = [
            (
                list(all_sample_sets_sorted.keys()).index(x),
                list(all_sample_sets_sorted.keys()).index(y),
            )
            for x, y in comparisons
            if x in all_sample_sets_sorted and y in all_sample_sets_sorted
        ]
        if comparisons_indexes == []:
            return pn.pane.Markdown(
                "**Select which sample sets to compare to see this plot.**"
            )
        if self.statistic == "Fst":
            data = tsm.ts.Fst(
                sample_sets_individuals,
                windows=windows,
                indexes=comparisons_indexes,
                mode=self.mode,
            )
            fig_text = "**Multiway Fst plot** - Lorem Ipsum"
        elif self.statistic == "divergence":
            data = tsm.ts.divergence(
                sample_sets_individuals,
                windows=windows,
                indexes=comparisons_indexes,
                mode=self.mode,
            )
            fig_text = "**Multiway divergence plot** - Lorem Ipsum"
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
                for i, j in comparisons_indexes
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
        return pn.Column(
            pn.panel(
                holomap.overlay("sspair").opts(legend_position="right"),
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(fig_text),
        )

    def sidebar(self) -> pn.Card:
        """Returns the content of the sidebar.

        Returns:
            pn.Card: The layout for the sidebar.
        """
        return pn.Card(
            self.param.mode,
            self.param.statistic,
            self.param.window_size,
            self.comparisons,
            self.param.colormap,
            collapsed=False,
            title="Multiway statistics plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class StatsPage(View):
    """This class defines a view for the "Statistics" page.

    Attributes:
    key (str):
        The unique key for the page (default: "stats").
    title (str):
        The title of the page (default: "Statistics").
    oneway (param.ClassSelector):
        A parameter to select the OnewayStats class for one-way plots.
    multiway (param.ClassSelector):
        A parameter to select the MultiwayStats class for multi-way plots.
    sample_sets (SampleSetsTable):  # Assuming SampleSetsTable exists elsewhere
        The SampleSetsTable object for managing sample set information.

    Methods:
    __panel__() -> pn.Column:
        Generates the panel for the "Statistics" page with one-way and
        multi-way plot accordions.
    sidebar() -> pn.Card:
        Creates the sidebar panel for the "Statistics"
    """

    key = "stats"
    title = "Statistics"
    oneway = param.ClassSelector(class_=OnewayStats)
    multiway = param.ClassSelector(class_=MultiwayStats)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.oneway = OnewayStats(datastore=self.datastore)
        self.multiway = MultiwayStats(datastore=self.datastore)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self):
        """Returns the main content of the page.

        Returns:
            pn.Column: The layout for the main content area.
        """
        return pn.Column(
            pn.Accordion(
                pn.Column(
                    self.oneway.tooltip,
                    self.oneway,
                    name="Oneway Statistics Plot",
                ),
                pn.Column(
                    self.multiway.tooltip,
                    self.multiway,
                    name="Multiway Statistics Plot",
                ),
                active=[0, 1],
            ),
        )

    def sidebar(self):
        """Returns the content of the sidebar.

        Returns:
            pn.Card: The layout for the sidebar.
        """
        return pn.Column(
            pn.pane.HTML(
                "<h2 style='margin: 0;'>Statistics</h2>",
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(
                (
                    "This section provides **population genetic "
                    "statistics** to analyze genetic variation "
                    "and divergence among sample sets.<br><br>"
                    "Use the controls below to customize the plots and "
                    "adjust parameters."
                ),
                sizing_mode="stretch_width",
            ),
            self.oneway.sidebar,
            self.multiway.sidebar,
            self.sample_sets.sidebar_table,
        )
