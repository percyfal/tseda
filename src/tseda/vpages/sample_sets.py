"""Sample sets editor page.

Panel showing a simple sample set editor page. The page consists of
an editable table showing the sample sets.

The sample sets table allows the user to edit the name and color of
each sample set. In addition, new sample sets can be added that allows
the user to reassign individuals to different sample sets in the
individuals table.

TODO:

- change from/to params to param.NumericTuple?
"""

import pandas as pd
import panel as pn
import param

from tseda import config
from tseda.datastore import SampleSetsTable
from tseda.model import SampleSet

from .core import View


class SampleSetsEditor(View):
    """Sample sets editor page."""

    default_columns = ["name", "color", "predefined"]
    editors = {k: None for k in default_columns}
    editors["color"] = {
        "type": "list",
        "values": config.COLORS,
        "valueLookup": True,
    }
    editors["name"] = {"type": "input", "validator": "unique", "search": True}
    formatters = {
        "color": {"type": "color"},
        "predefined": {"type": "tickCross"},
    }

    create_sample_set_textinput = param.String(
        doc="New sample set name. Press Enter (⏎) to create.",
        default=None,
        label="New sample set name",
    )

    page_size = param.Selector(objects=[10, 20, 50, 100], default=20)
    data = param.DataFrame()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_data()

    def _update_data(self):
        self.data = pd.DataFrame(
            self.datastore.individuals_table.sample_sets_list.rx.value
        )
        self.data.set_index(["id"], inplace=True)

    def update_ss(self, event):
        if event.column == "color":
            self.datastore.individuals_table.sample_sets_list.rx.value[
                event.row
            ].color = event.value
        elif event.column == "name":
            self.datastore.individuals_table.sample_sets_list.rx.value[
                event.row
            ].name = event.value

    @property
    def tooltip(self):
        return pn.widgets.TooltipIcon(
            value=(
                "The name and color of each sample set are editable. In the "
                "color column, select a color from the dropdown list. In the "
                "individuals table, you can assign individuals to sample sets."
            ),
        )

    @pn.depends("page_size", "create_sample_set_textinput")  # , "columns")
    def __panel__(self):
        if self.create_sample_set_textinput is not None:
            i = max(self.param.data.rx.value.index) + 1
            self.datastore.individuals_table.sample_sets_list.rx.value.append(
                SampleSet(
                    id=i,
                    name=self.create_sample_set_textinput,
                    color=config.COLORS[i % len(config.COLORS)],
                    predefined=False,
                )
            )
            self.create_sample_set_textinput = None
            self._update_data()
        table = pn.widgets.Tabulator(
            self.data,
            layout="fit_data_table",
            selectable=True,
            page_size=self.page_size,
            pagination="remote",
            margin=10,
            formatters=self.formatters,
            editors=self.editors,
        )
        table.on_edit(self.update_ss)
        return pn.Column(self.tooltip, table)

    def sidebar(self):
        return pn.Card(
            self.param.page_size,
            self.param.create_sample_set_textinput,
            title="Sample sets editor",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )

    def sidebar_table(self):
        table = pn.widgets.Tabulator(
            self.data,
            layout="fit_data_table",
            selectable=True,
            page_size=100,
            pagination="remote",
            margin=10,
            formatters=self.formatters,
            editors=self.editors,
            hidden_columns=["id"],
        )
        return pn.Card(
            pn.Column(self.tooltip, table),
            title="Sample sets table quick view",
            collapsed=True,
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class SampleSetsPage(View):
    key = "sample_sets"
    title = "Sample Sets"
    data = param.ClassSelector(class_=SampleSetsEditor)

    def __init__(self, **params):
        super().__init__(**params)
        self.data = SampleSetsEditor(datastore=self.datastore)

    def __panel__(self):
        return pn.Column(self.data)

    def sidebar(self):
        return pn.Column(self.data.sidebar)


class SampleSetsPageOld(View):
    key = "sample_sets"
    title = "Sample Sets"
    data = param.ClassSelector(class_=SampleSetsTable)

    def __init__(self, **params):
        super().__init__(**params)
        self.data = self.datastore.sample_sets_table

    def __panel__(self):
        return pn.Column(self.data)

    def sidebar(self):
        return pn.Column(self.data.sidebar)
