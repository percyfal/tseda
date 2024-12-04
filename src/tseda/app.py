"""Main application for tseda.

Provides the DataStoreApp class that is the main application for
tseda. The DataStoreApp subclasses the Viewer class from panel and
renders a panel.FastListTemplate object.
"""

import time

import daiquiri
import holoviews as hv
import panel as pn
import param
from holoviews import opts
from panel.viewable import Viewer

from tseda import config, datastore, vpages

logger = daiquiri.getLogger("tseda")

RAW_CSS = """
        .sidenav#sidebar {
            background-color: #15E3AC;
        }
        .title {
            font-size: var(--type-ramp-plus-2-font-size);
        }
    """
DEFAULT_PARAMS = {
    "site": "tseda",
    "theme_toggle": False,
}

pn.extension("tabulator")

hv.extension("bokeh")
hv.opts.defaults(
    opts.Scatter(color=config.PLOT_COLOURS[2]),
    opts.Points(color=config.PLOT_COLOURS[2]),
    opts.Histogram(
        fill_color=config.PLOT_COLOURS[0], line_color=config.PLOT_COLOURS[2]
    ),
    opts.Bars(color=config.PLOT_COLOURS[0], line_color=config.PLOT_COLOURS[2]),
    opts.Segments(color=config.PLOT_COLOURS[2]),
    opts.Curve(color=config.PLOT_COLOURS[2]),
    opts.Rectangles(
        fill_color=config.PLOT_COLOURS[0], line_color=config.PLOT_COLOURS[2]
    ),
)


class DataStoreApp(Viewer):
    """Main application class for tseda visualization app."""

    datastore = param.ClassSelector(class_=datastore.DataStore)

    title = param.String(doc="Application title")

    views = param.List(doc="What views to show on startup.")

    def __init__(self, **params):
        super().__init__(**params)
        t = time.time()
        logger.info("Initialising pages")
        self.pages = {
            page.title: page(datastore=self.datastore) for page in vpages.PAGES
        }
        self.spinner = pn.indicators.LoadingSpinner(
            value=True, width=50, height=50
        )
        logger.info(f"Initialised pages in {time.time() - t:.2f}s")

        updating = (
            self.datastore.individuals_table.data.rx.updating()
            | self.datastore.sample_sets_table.data.rx.updating()
        )
        updating.rx.watch(
            lambda updating: pn.state.curdoc.hold()
            if updating
            else pn.state.curdoc.unhold()
        )

    @param.depends("views")
    def view(self):
        """Main application view that renders a radio button group on
        top with links to pages. Each page consists of a main content
        page with plots and sidebars that provide user options for
        configuring plots and outputs."""
        page_titles = list(self.pages.keys())
        header_selector = pn.widgets.RadioButtonGroup(
            options=page_titles,
            value=page_titles[0],
            name="Select Page",
            button_type="success",
        )

        @pn.depends(header_selector.param.value)
        def get_content(selected_page):
            yield self.spinner
            yield self.pages[selected_page].servable

        @pn.depends(header_selector.param.value)
        def get_sidebar(selected_page):
            yield self.spinner
            yield self.pages[selected_page].sidebar

        self._template = pn.template.FastListTemplate(
            title=self.datastore.tsm.name[:75] + "..."
            if len(self.datastore.tsm.name) > 75
            else self.datastore.tsm.name,
            header=[header_selector],
            sidebar=get_sidebar,
            main=get_content,
            raw_css=[RAW_CSS],
            **DEFAULT_PARAMS,
        )
        return self._template
