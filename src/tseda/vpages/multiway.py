"""Multiway population genetics statistics visualization module."""

import holoviews as hv
import panel as pn
import param

import tseda.widgets as widgets
from tseda import config
from tseda.widgets.mixins import TooltipMixin

from .core import View

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_width")


class MultiwayStats(widgets.MultiwayHoloviewsStats, TooltipMixin):
    _tooltip = (
        "Multiway statistical plot. The colors can be modified "
        "in the colormap dropdown list."
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
    multiway (param.ClassSelector):
        A parameter to select the MultiwayStats class for multi-way plots.
    sample_sets (SampleSetsTable):  # Assuming SampleSetsTable exists elsewhere
        The SampleSetsTable object for managing sample set information.

    Methods:
    __panel__() -> pn.Column:
        Generates the panel for the "Statistics" page multi-way plot accordion.
    sidebar() -> pn.Card:
        Creates the sidebar panel for the "Statistics"
    """

    key = "multiway"
    title = "Multiway"
    multiway = param.ClassSelector(class_=MultiwayStats)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.line = MultiwayStats(
            datastore=self.datastore, sizing_mode="stretch_width"
        )
        self.box = MultiwayStats(
            datastore=self.datastore,
            sizing_mode="stretch_width",
            plotfun="box",
            height=int(self.line.height * 1.5),
        )
        self.kde = MultiwayStats(
            datastore=self.datastore,
            sizing_mode="stretch_width",
            plotfun="kde",
            height=int(self.line.height * 1.5),
        )
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self):
        """Returns the main content of the page.

        Returns:
            pn.Column: The layout for the main content area.
        """
        gspec = pn.GridSpec(ncols=2, nrows=3, sizing_mode="stretch_width")
        gspec[0, :] = pn.Column(self.line.tooltip, self.line)
        gspec[1:3, 0] = self.box
        gspec[1:3, 1] = self.kde
        return pn.Column(
            gspec,
            name="Multiway Statistics Plot",
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
            self.line.sidebar,
            self.sample_sets.sidebar_table,
        )
