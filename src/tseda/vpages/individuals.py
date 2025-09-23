"""Individuals editor page.

Panel showing a simple individuals editor page. The page consists of
two main components: a map showing the distribution of individuals
and a table showing the individuals.

The individuals table allows the user to toggle individuals for
inclusion/exclusion, and reassign individuals to new sample set
combinations.
"""

import panel as pn
import param

from tseda.datastore import IndividualsTable, SampleSetsTable

from .core import View
from .map import GeoMap


class IndividualsPage(View):
    """This class represents a view for the individuals page.

    Attributes:
        key (str): A unique identifier for this view.
        title (str): The title displayed for this view.
        sample_sets_table (param.ClassSelector): A reference to a
            `SampleSetsTable` object containing information about sample sets.
        individuals_table (param.ClassSelector): A reference to an
            `IndividualsTable` object managing individual data and filtering
            options.
        geomap (param.ClassSelector): A reference to a `GeoMap` object
        displaying
            geographical locations and sample set affiliations (optional).

    Methods:
        __panel__(): Defines the layout of the view using Panel components.
        sidebar(): Defines the sidebar content with descriptions and controls.
            Contains:
            sample_sets_accordion_toggled(event): Handles the toggling event
            of the sample sets accordion
    """

    key = "individuals and sets"
    title = "Individuals & sets"
    sample_sets_table = param.ClassSelector(class_=SampleSetsTable)
    individuals_table = param.ClassSelector(class_=IndividualsTable)
    geomap = param.ClassSelector(class_=GeoMap)

    def __init__(self, **params):
        super().__init__(**params)
        self.geomap = GeoMap(datastore=self.datastore)
        self.sample_sets_table = self.datastore.sample_sets_table
        self.individuals_table = self.datastore.individuals_table
        self.individuals_table.sample_sets_table = self.sample_sets_table

    @pn.depends(
        "individuals_table.sample_select.value",
        "individuals_table.refresh_button.value",
    )
    def __panel__(self) -> pn.Column:
        """Defines the layout of the view using Panel components. This method
        is called dynamically when dependent parameters change.

        Returns:
            pn.Column: A Panel column containing the layout of the view.
        """
        sample_sets_accordion = pn.Accordion(
            pn.Column(
                self.sample_sets_table,
                sizing_mode="stretch_width",
                name="Sample Sets Table",
            ),
            max_width=400,
            active=[0],
        )

        def sample_sets_accordion_toggled(event):
            """Handles the toggling event of the sample sets accordion.

            This function dynamically adjusts the maximum width of the
            accordion based on its active state. If the accordion is closed
            (active state is an empty list), the width is set to 180 pixels.
            Otherwise, when the accordion is open, the width is set to 400
            pixels.

            Arguments:
                event (param.Event): The event object triggered by the
                accordion's toggle. NOTE: event should not be provided, but
                Panel
                does not recognize the function without it.
            """
            if sample_sets_accordion.active == []:
                sample_sets_accordion.max_width = 180
            else:
                sample_sets_accordion.max_width = 400

        sample_sets_accordion.param.watch(
            sample_sets_accordion_toggled, "active"
        )
        p = pn.Column(
            pn.Row(
                pn.Accordion(
                    pn.Column(
                        pn.Column(self.geomap, sizing_mode="scale_both"),
                        pn.pane.Markdown(
                            "**Map** - Displays the geographical locations "
                            "where samples were collected and visually "
                            "represents their group sample affiliations "
                            "through colors.",
                            sizing_mode="stretch_both",
                        ),
                        min_width=300,
                        min_height=600,
                        sizing_mode="stretch_both",
                        name="Geomap",
                    ),
                    active=[0],
                    sizing_mode="stretch_height",
                ),
                pn.Spacer(sizing_mode="stretch_width", max_width=5),
                sample_sets_accordion,
            ),
            pn.Accordion(
                pn.Column(self.individuals_table, name="Individuals Table"),
                active=[0],
                sizing_mode="stretch_height",
                min_height=1200,
            ),
            pn.Spacer(sizing_mode="stretch_both", max_height=5),
        )
        return p

    def sidebar(self) -> pn.Column:
        """Defines the content for the sidebar of the view containing
        descriptive text and control elements.

        Returns:
            pn.Column: A Panel column containing the sidebar content.
        """
        return pn.Column(
            pn.pane.HTML(
                "<h2 style='margin: 0;'>Individuals & sets</h2>",
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(
                (
                    "This section allows you to manage and explore"
                    "individual samples in your dataset "
                    "and customize Sample Sets.<br><br>"
                    "Use the controls below to customize the plots,"
                    "adjust parameters, and add new samples."
                ),
                sizing_mode="stretch_width",
            ),
            self.individuals_table.refresh_button,
            self.geomap.sidebar,
            self.sample_sets_table.sidebar,
            self.individuals_table.options_sidebar,
            self.individuals_table.modification_sidebar,
        )
