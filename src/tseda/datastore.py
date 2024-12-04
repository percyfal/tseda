import random

import daiquiri
import pandas as pd
import panel as pn
import param
from panel.viewable import Viewer
from tsbrowse import model

from tseda import config
from tseda.model import Individual, SampleSet

from .gnn import windowed_genealogical_nearest_neighbours

logger = daiquiri.getLogger("tseda")


def make_individuals_table(tsm):
    result = []
    for ts_ind in tsm.ts.individuals():
        ind = Individual(individual=ts_ind)
        result.append(ind)
    return IndividualsTable(table=pd.DataFrame(result))


def make_sample_sets_table(tsm):
    result = []
    for ts_pop in tsm.ts.populations():
        ss = SampleSet(id=ts_pop.id, population=ts_pop, predefined=True)
        result.append(ss)
    return SampleSetsTable(table=pd.DataFrame(result))


def preprocess(tsm):
    """Take a tsbrowse.TSModel and make individuals and sample sets tables."""
    logger.info(
        "Preprocessing data: making individuals and sample sets tables"
    )
    individuals_table = make_individuals_table(tsm)
    sample_sets_table = make_sample_sets_table(tsm)
    return individuals_table, sample_sets_table


class IndividualsTable(Viewer):
    """Class to hold and view individuals and perform calculations to
    change filters."""

    columns = [
        "name",
        "population",
        "sample_set_id",
        "selected",
        "longitude",
        "latitude",
    ]
    editors = {k: None for k in columns}  # noqa
    editors["sample_set_id"] = {
        "type": "number",
        "valueLookup": True,
    }
    editors["selected"] = {
        "type": "list",
        "values": [False, True],
        "valuesLookup": True,
    }
    formatters = {"selected": {"type": "tickCross"}}

    table = param.DataFrame()

    page_size = param.Selector(
        objects=[10, 20, 50, 100, 200, 500],
        default=20,
        doc="Number of rows per page to display",
    )
    sample_select = pn.widgets.MultiChoice(
        name="Select sample sets",
        description="Select samples based on the sample set ID.",
        options=[],
    )
    population_from = param.Integer(
        label="Population ID",
        default=None,
        bounds=(0, None),
        doc=("Reassign individuals with this population ID."),
    )
    sample_set_to = param.Integer(
        label="New sample set ID",
        default=None,
        bounds=(0, None),
        doc=("Reassign individuals to this sample set ID."),
    )
    mod_update_button = pn.widgets.Button(name="Update")

    filters = {
        "name": {"type": "input", "func": "like", "placeholder": "Enter name"},
        "population": {
            "type": "input",
            "func": "like",
            "placeholder": "Enter ID",
        },
        "sample_set_id": {
            "type": "input",
            "func": "like",
            "placeholder": "Enter ID",
        },
        "selected": {
            "type": "tickCross",
            "tristate": True,
            "indeterminateValue": None,
            "placeholder": "Enter True/False",
        },
    }

    def __init__(self, **params):
        super().__init__(**params)
        self.table.set_index(["id"], inplace=True)
        self.data = self.param.table.rx()
        self.sample_select.options = self.sample_set_indices()
        self.sample_select.value = self.sample_set_indices()

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

    def sample_set_indices(self):
        """Return indices of sample groups."""
        return sorted(self.data.rx.value["sample_set_id"].unique().tolist())

    def sample_sets(self):
        sample_sets = {}
        samples = []
        inds = self.data.rx.value
        for _, ind in inds.iterrows():
            if not ind.selected:
                continue
            sample_set = ind.sample_set_id
            if sample_set not in sample_sets:
                sample_sets[sample_set] = []
            sample_sets[sample_set].extend(ind.nodes)
            samples.extend(ind.nodes)
        return samples, sample_sets

    def get_sample_sets(self, indexes=None):
        """Return list of sample sets and their samples."""
        samples, sample_sets = self.sample_sets()
        if indexes:
            return [sample_sets[i] for i in indexes]
        return [sample_sets[i] for i in sample_sets]

    @property
    def sample2ind(self):
        """Map sample (tskit node) ids to individual ids"""
        inds = self.data.rx.value
        d = {}
        for index, ind in inds.iterrows():
            for node in ind.nodes:
                d[node] = index
        return d

    def samples(self):
        """Return all samples"""
        for _, ind in self.data.rx.value.iterrows():
            for node in ind.nodes:
                yield node

    def loc(self, i):
        """Return individual by index"""
        return self.data.rx.value.loc[i]

    @pn.depends("page_size", "sample_select.value", "mod_update_button.value")
    def __panel__(self):
        self.data.rx.value["selected"] = False
        if (
            isinstance(self.sample_select.value, list)
            and self.sample_select.value
        ):
            for sample_set_id in self.sample_select.value:
                self.data.rx.value.loc[
                    self.data.rx.value.sample_set_id == sample_set_id,
                    "selected",
                ] = True
        if self.sample_set_to is not None:
            if self.population_from is not None:
                try:
                    self.table.loc[
                        self.table["population"] == self.population_from,  # pyright: ignore[reportIndexIssue]
                        "sample_set_id",
                    ] = self.sample_set_to
                except IndexError:
                    logger.error("No such population %i", self.population_from)
            else:
                logger.info("No population defined")
        data = self.data[self.columns]

        table = pn.widgets.Tabulator(
            data,
            pagination="remote",
            layout="fit_columns",
            selectable=True,
            page_size=self.page_size,
            formatters=self.formatters,
            editors=self.editors,
            margin=10,
            text_align={col: "right" for col in self.columns},
            header_filters=self.filters,
        )
        return pn.Column(self.tooltip, table)

    def options_sidebar(self):
        return pn.Card(
            self.param.page_size,
            self.sample_select,
            collapsed=False,
            title="Individuals table options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )

    modification_header = pn.pane.Markdown("#### Batch reassign indivuduals:")

    def modification_sidebar(self):
        return pn.Card(
            pn.Column(
                self.modification_header,
                pn.Row(self.param.population_from, self.param.sample_set_to),
                self.mod_update_button,
            ),
            collapsed=False,
            title="Data modification",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class SampleSetsTable(Viewer):
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

    warning_pane = pn.pane.Alert(
        "This sample set name already exists, pick a unique name.",
        alert_type="warning",
        visible=False,
    )

    page_size = param.Selector(objects=[10, 20, 50, 100], default=20)

    table = param.DataFrame()

    def __init__(self, **params):
        super().__init__(**params)
        self.table.set_index(["id"], inplace=True)
        self.data = self.param.table.rx()

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
            previous_names = [
                self.table.name[i] for i in range(len(self.table))
            ]
            if self.create_sample_set_textinput in previous_names:
                self.warning_pane.visible = True
            else:
                previous_colors = [
                    self.table.color[i] for i in range(len(self.table))
                ]
                unused_colors = [
                    color
                    for color in config.COLORS
                    if color not in previous_colors
                ]
                if len(unused_colors) != 0:
                    colors = unused_colors
                else:
                    colors = config.COLORS
                self.warning_pane.visible = False
                i = max(self.param.table.rx.value.index) + 1
                self.param.table.rx.value.loc[i] = [
                    self.create_sample_set_textinput,
                    colors[random.randint(0, len(colors) - 1)],
                    False,
                ]
                self.create_sample_set_textinput = None
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
        return pn.Column(self.tooltip, table)

    def sidebar_table(self):
        table = pn.widgets.Tabulator(
            self.data,
            layout="fit_data_table",
            selectable=True,
            page_size=10,
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

    def sidebar(self):
        return pn.Column(
            pn.Card(
                self.param.page_size,
                self.param.create_sample_set_textinput,
                title="Sample sets table options",
                collapsed=False,
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.warning_pane,
        )

    @property
    def color(self):
        """Return the color of all sample sets as a dictionary"""
        d = {}
        for index, row in self.data.rx.value.iterrows():
            d[index] = row.color
        return d

    @property
    def color_by_name(self):
        """Return the color of all sample sets as a dictionary with
        sample set names as keys"""
        d = {}
        for _, row in self.data.rx.value.iterrows():
            d[row["name"]] = row.color
        return d

    @property
    def names(self):
        """Return the names of all sample sets as a dictionary"""
        d = {}
        for index, row in self.data.rx.value.iterrows():
            d[index] = row["name"]
        return d

    @property
    def names2id(self):
        """Return the sample sets as dictionary with names as keys,
        ids as values"""
        d = {}
        for index, row in self.data.rx.value.iterrows():
            d[row["name"]] = index
        return d

    def loc(self, i):
        """Return sample set by index"""
        return self.data.rx.value.loc[i]


class DataStore(Viewer):
    tsm = param.ClassSelector(class_=model.TSModel)
    individuals_table = param.ClassSelector(class_=IndividualsTable)
    sample_sets_table = param.ClassSelector(class_=SampleSetsTable)

    views = param.List(constant=True)

    @property
    def color(self):
        """Return colors of selected individuals"""
        color = pd.merge(
            self.individuals_table.data.rx.value,
            self.sample_sets_table.data.rx.value,
            left_on="sample_set_id",
            right_index=True,
        )
        return color.loc[color.selected].color

    def haplotype_gnn(self, focal_ind, windows=None):
        samples, sample_sets = self.individuals_table.sample_sets()
        ind = self.individuals_table.loc(focal_ind)
        hap = windowed_genealogical_nearest_neighbours(
            self.tsm.ts, ind.nodes, sample_sets, windows=windows
        )
        dflist = []
        sample_set_names = [
            self.sample_sets_table.loc(i)["name"] for i in sample_sets
        ]
        if windows is None:
            for i in range(hap.shape[0]):
                x = pd.DataFrame(hap[i, :])
                x = x.T
                x.columns = sample_set_names
                x["haplotype"] = i
                x["start"] = 0
                x["end"] = self.tsm.ts.sequence_length
                dflist.append(x)
        else:
            for i in range(hap.shape[1]):
                x = pd.DataFrame(hap[:, i, :])
                x.columns = sample_set_names
                x["haplotype"] = i
                x["start"] = windows[0:-1]
                x["end"] = windows[1:]
                dflist.append(x)
        df = pd.concat(dflist)
        df.set_index(["haplotype", "start", "end"], inplace=True)
        return df

    # Not needed? Never used?
    def __panel__(self):
        return pn.Row(
            self.individuals_table,
            self.sample_sets_table,
        )
