"""Population genetic statistics.

TODO:
- add more stats
- add xwheel zoom and pan
- box plots
- distribution plots
"""

import holoviews as hv
import panel as pn
import param

import tseda.widgets as widgets
from tseda import config
from tseda.widgets.mixins import TooltipMixin

from .core import View

hv.extension("bokeh")
pn.extension(sizing_mode="stretch_width")


class OnewayStats(widgets.OnewayHoloviewsStats, TooltipMixin):
    _tooltip = (
        "Oneway statistical plot. The colors can be modified "
        "in the sample set editor page."
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
        self.oneway = OnewayStats(
            datastore=self.datastore, sizing_mode="stretch_width"
        )
        self.multiway = MultiwayStats(
            datastore=self.datastore, sizing_mode="stretch_width"
        )
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
