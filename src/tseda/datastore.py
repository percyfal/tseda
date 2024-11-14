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


def make_sample_sets_list(tsm):
    result = []
    for ts_pop in tsm.ts.populations():
        ss = SampleSet(id=ts_pop.id, population=ts_pop, predefined=True)
        result.append(ss)
    return result


def make_individuals_table(tsm):
    result = []
    for ts_ind in tsm.ts.individuals():
        ind = Individual(individual=ts_ind)
        result.append(ind)
    tab = IndividualsTable(
        table=pd.DataFrame(result),
        sample_sets_list_=make_sample_sets_list(tsm),
    )
    return tab


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
        "population_name",
        "sample_set_id",
        "sample_set_name",
        "sample_set_color",
        "selected",
        "longitude",
        "latitude",
    ]
    editors = {k: None for k in columns}  # noqa
    editors["sample_set_id"] = {
        "type": "list",
        "values": [],
        "valueLookup": True,
    }
    editors["selected"] = {
        "type": "list",
        "values": [False, True],
        "valuesLookup": True,
    }
    formatters = {"selected": {"type": "tickCross"}}

    table = param.DataFrame()
    sample_sets_list_ = param.List(default=[], item_type=SampleSet)

    page_size = param.Selector(
        objects=[10, 20, 50, 100, 200, 500],
        default=100,
        doc="Number of rows per page to display",
    )
    toggle = param.Integer(
        default=None, bounds=(0, None), doc="Toggle sample set by index"
    )
    population_from = param.Integer(
        default=None,
        bounds=(0, None),
        doc=(
            "Batch reassign individual from this `population` "
            "to the index given in the `sample_set_to` parameter"
        ),
    )
    sample_set_to = param.Integer(
        default=None,
        bounds=(0, None),
        doc=(
            "Batch reassign individuals in the index given in "
            "the `sample_set_from` parameter to this sample set. "
            "Update will only take place when both fields are set."
        ),
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.table.set_index(["id"], inplace=True)
        try:
            ss_d = {ss.id: ss for ss in self.sample_sets_list_}
            for i in self.table.index:
                ss = ss_d[self.table.loc[i, "sample_set_id"]]
                self.table.loc[i, "population_name"] = ss.name
                self.table.loc[i, "sample_set_name"] = ss.name
                self.table.loc[i, "sample_set_color"] = ss.color
        except KeyError:
            logger.error("Sample set not found")
        self.data = self.param.table.rx()
        self.sample_sets_list = self.param.sample_sets_list_.rx()

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

    @pn.depends("page_size", "toggle", "sample_set_to")
    def __panel__(self):
        if self.toggle is not None:
            self.data.rx.value.loc[
                self.toggle == self.data.rx.value.sample_set_id, "selected"
            ] = not self.data.rx.value.loc[self.toggle, "selected"]
            self.toggle = None
        if self.sample_set_to is not None:
            if self.population_from is not None:
                ii = self.data.rx.value["population"] == self.population_from
                self.data.rx.value.loc[
                    ii,
                    "sample_set_id",
                ] = self.sample_set_to

                self.table.loc[ii, "sample_set_name"] = (
                    self.sample_sets_list.rx.value[self.sample_set_to].name
                )
                self.table.loc[ii, "sample_set_color"] = (
                    self.sample_sets_list.rx.value[self.sample_set_to].color
                )
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
            text_align={"selected": "center"},
        )
        return pn.Column(self.tooltip, table)

    def sidebar(self):
        return pn.Card(
            self.param.page_size,
            self.param.toggle,
            self.param.population_from,
            self.param.sample_set_to,
            collapsed=False,
            title="Individuals table options",
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
            i = max(self.param.table.rx.value.index) + 1
            self.param.table.rx.value.loc[i] = [
                self.create_sample_set_textinput,
                config.COLORS[0],
                False,
            ]
            self.create_sample_set_textinput = None
        table = pn.widgets.Tabulator(
            self.data,
            layout="fit_data_table",
            selectable=True,
            page_size=100,
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

    def sidebar(self):
        return pn.Card(
            self.param.page_size,
            self.param.create_sample_set_textinput,
            title="Sample sets table options",
            collapsed=False,
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
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

    def update_individuals_table(self, column, row, value):
        print("editing sample sets")
        print(column, row, value)

    # Not needed? Never used?
    def __panel__(self):
        return pn.Row(
            self.individuals_table,
            self.sample_sets_table,
        )
