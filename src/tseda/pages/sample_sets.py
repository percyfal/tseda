"""Sample sets editor page.

Panel showing a simple sample set editor page. The page consists of
three main components: a map showing the distribution of individuals,
a table showing the sample sets, and a table showing the individuals.

The sample sets table allows the user to edit the name and color of
each sample set. In addition, new sample sets can be added that allows
the user to reassign individuals to different sample sets in the
individuals table.

The individuals table allows the user to toggle individuals for
inclusion/exclusion, and reassign individuals to new sample set
combinations.
"""

import matplotlib.colors as mcolors
import panel as pn
import param

from .map import GeoMap

pn.extension("tabulator")

palette = list(mcolors.CSS4_COLORS.keys())


class IndividualsTable(param.Parameterized):
    columns = [
        "name",
        "population",
        "sample_set_id",
        "selected",
        "longitude",
        "latitude",
    ]
    individuals_editors = {k: None for k in columns}
    individuals_editors["sample_set_id"] = {
        "type": "list",
        "values": [],
        "valueLookup": True,
    }
    individuals_editors["selected"] = {
        "type": "list",
        "values": [False, True],
        "valuesLookup": True,
    }
    individuals_formatters = {"selected": {"type": "tickCross"}}

    page_size = param.Selector(objects=[10, 20, 50, 100])

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm

        self._table = self.tsm.get_individuals(astype="df", deselected=True)[
            self.columns
        ]
        self.individuals_editors["sample_set_id"]["values"] = (
            tsm.sample_sets_view().index.tolist()
        )

    @property
    def table(self):
        return self._table

    def update_individual(self, event):
        self.tsm.update_individual(event.row, event.column, event.value)
        self._table = self.tsm.get_individuals(astype="df", deselected=True)[
            self.columns
        ]
        self.individuals_editors["sample_set_id"]["values"] = (
            self.tsm.sample_sets_view().index.tolist()
        )

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "Individuals table with columns relevant for modifying plots. "
                "The `population_id` column is immutable and displays the  "
                "population id of the individual, as assigned during "
                "inference. The `sample_set_id` column is editable and can "
                "be assigned to a sample set id from the sample set table "
                "through a drop-down list by clicking on a cell. "
                "The `selected` column indicates whether an individual is  "
                "included in the analyses or not, and can be toggled to  "
                "exclude/include individuals of choice. Individuals lacking "
                "geolocation coordinates (`longitude`/`latitude`) are not  "
                "displayed in the GeoMap plots."
            ),
        )

    @param.depends("page_size")
    def panel(self):
        table = pn.widgets.Tabulator(
            self.table,
            layout="fit_columns",
            selectable=True,
            pagination="remote",
            page_size=self.page_size,
            editors=self.individuals_editors,
            formatters=self.individuals_formatters,
            text_align={"selected": "center"},
        )
        table.on_edit(self.update_individual)
        return pn.Column(self.tooltip, table)


class SampleSetTable(param.Parameterized):
    sample_editors = {
        "color": {
            "type": "list",
            "values": list(mcolors.CSS4_COLORS.keys()),
            "valueLookup": True,
        }
    }
    sample_formatters = {"color": {"type": "color"}}

    create_sample_set_textinput = param.String(
        doc="New sample set name. Press Enter (⏎) to create.",
        default="",
        label="New sample set name",
    )

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.update_table()

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "The name and color of each sample set are editable. In the "
                "color column, select a color from the dropdown list. In the "
                "individuals table, you can assign individuals to sample sets."
            ),
        )

    def update_table(self, **kwargs):
        self._table = pn.widgets.Tabulator(
            self.tsm.sample_sets_view(),
            layout="fit_columns",
            selectable=True,
            pagination="remote",
            page_size=10,
            editors=self.sample_editors,
            formatters=self.sample_formatters,
        )
        self._table.on_edit(self.update_sample_set)

    @property
    def table(self):
        self.update_table()
        return self._table

    def update_sample_set(self, event):
        self.tsm.update_sample_set(event.row, event.column, event.value)

    @param.depends("create_sample_set_textinput")
    def panel(self, *args, **kwargs):
        if self.create_sample_set_textinput:
            self.tsm.create_sample_set(self.create_sample_set_textinput)
            self.create_sample_set_textinput = ""
        return pn.Column(self.tooltip, self.table)


def page(tsm):
    geomap = GeoMap(tsm)
    ss_table = SampleSetTable(tsm)
    ind_table = IndividualsTable(tsm)

    layout = pn.Column(
        pn.Row(
            pn.Column(
                geomap.param,
                geomap.plot,
            ),
            pn.Column(
                ss_table.param,
                ss_table.panel,
            ),
        ),
        pn.Row(
            pn.Column(
                ind_table.param,
                ind_table.panel,
            ),
        ),
    )

    return layout
