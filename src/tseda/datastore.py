"""This module provides a collection of classes and functions for analyzing and
visualizing population genetic data. It uses the `tsbrowse` library for working
with TreeSequence data and the `panel` library for creating interactive
visualizations.

Key Classes:

- `SampleSetsTable`: Manages and displays information about sample sets,
including
    their names, colors, and predefined status.
- `IndividualsTable`: Handles individual data, including their population,
sample set
    assignments, and selection status. Enables filtering and modification of
    individual
    attributes.
- `DataStore`: Provides access to the underlying TreeSequence data, sample
sets,
    and individuals data. Also includes methods for calculating haplotype
    GNNs and
    retrieving sample and population information.

Methods:

- `make_individuals_table`: Creates an `IndividualsTable` object from a given
TreeSequence.
- `make_sample_sets_table`: Creates a `SampleSetsTable` object from a given
TreeSequence.
- `preprocess`: Calls `make_individuals_table`and `make_sample_sets_table`.
"""

import random
from typing import Dict, List, Optional, Tuple

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


class SampleSetsTable(Viewer):
    """SampleSetsTable class represents a table for managing sample sets.

    Attributes:
        columns (list):
            The default columns displayed in the table (["name", "color",
            "predefined"]).
        editors (dict):
            Dictionary specifying editor types for each column in the table.
        formatters (dict):
            Dictionary defining formatters for each column.
        create_sample_set_textinput (String):
            Parameter for entering a new sample set name (default=None).
        create_sample_set_button (pn.widget.Button):
            Button to create sample set.
        sample_set_warning (pn.pane.Alert):
            Warning alert for duplicate sample set names.
        table (param.DataFrame):
            Underlying DataFrame holding sample set data.

    Methods:
        tooltip() -> pn.widgets.TooltipIcon:
            Returns a tooltip for the table.
        def __panel__():
            Creates the main panel for the table with functionalities.
        get_ids() -> List:
            Returns a list of sample set IDs.
        sidebar_table() -> pn.Column:
            Generates a sidebar table with quick view functionalities.
        sidebar() - > pn.Column:
            Creates the sidebar with options for managing sample sets.
        color_by_name (dict):
            Returns a dictionary with sample set colors as key-value pairs
            (name-color).
        names (dict):
            Returns a dictionary with sample set names as key-value pairs
            (index-name).
        loc(self, i: int) -> pd.core.series.Series:
            Returns a pd.core.series.Series (row) of a dataframe for a
            specific id
    """

    columns = ["name", "color", "predefined"]
    editors = {k: None for k in columns}
    editors["color"] = {
        "type": "list",
        "values": config.COLORS,
        "valueLookup": True,
    }
    editors = {
        "name": {"type": "input", "validator": "unique", "search": True},
        "color": {
            "type": "list",
            "values": [
                {
                    "value": color,
                    "label": (
                        f'<div style="background-color:{color}; '
                        f'width: 100%; height: 20px;"></div>'
                    ),
                }
                for color in config.COLORS
            ],
        },
        "predefined": {"type": "tickCross"},
        "valueLookup": True,
    }
    formatters = {
        "color": {"type": "color"},
        "predefined": {"type": "tickCross"},
    }
    create_sample_set_textinput = param.String(
        doc="Enter name of new sample set.",
        default=None,
        label="Create new sample set",
    )
    create_sample_set_button = pn.widgets.Button(
        description="Create new sample set.",
        name="Create",
        button_type="success",
        align="end",
    )
    sample_set_warning = pn.pane.Alert(
        "This sample set name already exists, pick a unique name.",
        alert_type="warning",
        visible=False,
    )
    table = param.DataFrame()

    def __init__(self, **params):
        super().__init__(**params)
        self.table.set_index(["sample_set_id"], inplace=True)
        self.data = self.param.table.rx()

    @property
    def tooltip(self) -> pn.widgets.TooltipIcon:
        """Returns a TooltipIcon widget containing instructions for editing
        sample set names and colors, and assigning individuals to sample sets.

        Returns:
            pn.widgets.TooltipIcon: A TooltipIcon widget displaying the
            instructions.
        """
        return pn.widgets.TooltipIcon(
            value=(
                "The name and color of each sample set are editable. In the "
                "color column, select a color from the dropdown list. In the "
                "individuals table, you can assign individuals to sample sets."
            ),
        )

    def create_new_sample_set(self):
        """Creates a new sample set with the provided name in the
        create_sample_set_textinput widget, if a name is entered and it's not
        already in use."""
        if self.create_sample_set_textinput is not None:
            previous_names = [
                self.table.name[i] for i in range(len(self.table))
            ]
            if self.create_sample_set_textinput in previous_names:
                self.sample_set_warning.visible = True
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
                self.sample_set_warning.visible = False
                i = max(self.param.table.rx.value.index) + 1
                self.param.table.rx.value.loc[i] = [
                    self.create_sample_set_textinput,
                    colors[random.randint(0, len(colors) - 1)],
                    False,
                ]
                self.create_sample_set_textinput = None

    def get_ids(self) -> List:
        """Returns the sample set IDs.

        Returns:
            List: A list of the sample set IDs as integers

        Raises:
            TypeError: If the sample set table is not a valid
            Dataframe (not yet populated)
        """
        if isinstance(self.table, pd.DataFrame):
            return self.table.index.values.tolist()
        else:
            raise TypeError("self.table is not a valid pandas DataFrame.")

    @property
    def color_by_name(self) -> Dict[str, str]:
        """Return the color of all sample sets as a dictionary with sample set
        names as keys.

        Returns:
            Dict: dictionary of
        """
        d = {}
        for _, row in self.data.rx.value.iterrows():
            d[row["name"]] = row.color
        return d

    @property
    def names(self) -> Dict[int, str]:
        # TODO: see why this is called 6 times in a row - unecessary
        """Return the names of all sample sets as a dictionary.

        Returns:
            Dict: dictionary of indices (int) as keys and
            names (str) as values
        """
        d = {}
        for index, row in self.data.rx.value.iterrows():
            d[index] = row["name"]

        return d

    def loc(self, i: int) -> pd.core.series.Series:
        """Returns sample set pd.core.series.Series object (dataframe row) by
        index.

        Arguments:
            i: Index for the sample set wanted

        Returns:
            pd.core.series.Series object:
                Containing name, color and predefined status.
        """
        return self.data.rx.value.loc[i]

    @pn.depends("create_sample_set_button.value")
    def __panel__(self) -> pn.Column:
        """Returns the main content of the page which is retrieved from the
        `datastore.tsm.ts` attribute.

        Returns:
            pn.Column: The layout for the main content area.
        """
        self.create_new_sample_set()

        table = pn.widgets.Tabulator(
            self.data,
            layout="fit_data_table",
            selectable=True,
            page_size=10,
            pagination="remote",
            margin=10,
            formatters=self.formatters,
            editors=self.editors,
            configuration={
                "rowHeight": 40,
            },
            height=500,
        )
        return pn.Column(
            self.tooltip,
            table,
        )

    def sidebar_table(self) -> pn.Card:
        """Generates a sidebar table with quick view functionalities.

        Returns:
            pn.Card: The layout for the sidebar.
        """
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

    def sidebar(self) -> pn.Column:
        """Returns the content of the sidebar.

        Returns:
            pn.Column: The layout for the sidebar.
        """
        return pn.Column(
            pn.Card(
                self.param.create_sample_set_textinput,
                self.create_sample_set_button,
                title="Sample sets table options",
                collapsed=False,
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.sample_set_warning,
        )


class IndividualsTable(Viewer):
    """Class represents a table for managing individuals and perform
    calculations to change filters.

    Attributes:
        sample_sets_table (param.ClassSelector):
            ClassSelector for the SampleSetsTable class.
        columns (list):
            The default columns displayed in the table (["name", "color",
            "predefined"]).
        editors (dict):
            Dictionary specifying editor types for each column in the table.
        formatters (dict):
            Dictionary defining formatters for each column.
        filters (dict):
            Filter configurations for the columns.
        table (param.DataFrame):
            Underlying data stored as a DataFrame.
        page_size (param.Selector):
            Number of rows per page to display.
        sample_select (pn.widgets.MultiChoice):
            Widget for selecting sample sets.
        population_from (pn.widgets.Select):
            Widget for selecting the original population ID.
        sample_set_to (pn.widgets.Select):
            Widget for selecting the new sample set ID.
        mod_update_button (pn.widgets.Button):
            Button to apply reassignment of population IDs.
        refresh_button (pn.widgets.Button):
            Button to refresh the table view.
        restore_button (pn.widgets.Button):
            Button to restore data to its original state.
        data_mod_warning (pn.pane.Alert):
            Warning alert for invalid modifications.


    Methods:

        tooltip()  -> pn.widgets.TooltipIcon :
            Returns a TooltipIcon widget containing information about the
            individuals
            table and how to edit it.

        sample_sets(only_selected: Optional[bool] = True):
            Returns a dictionary with a sample set id to samples list mapping.

        get_population_ids() -> List[int]:
            Returns a sorted list of unique population IDs present in the data.

        get_sample_set_ids() -> List[int]:
            Returns a sorted list of unique sample set IDs present in the data.
            This method combines IDs from two sources:
                1. Underlying data ("sample_set_id" column).
                2. Optional SampleSetsTable object (if defined).

        sample2ind -> Dict[int, int]:
            Creates a dictionary mapping sample (tskit node) IDs to
            individual IDs.

        samples():
            Yields all sample (tskit node) IDs present in the data.

        loc(i: int) -> pd.core.series.Series:
            Returns the individual data (pd.Series) for a specific index (ID).

        reset_modification():
            Resets the "sample_set_id" column to the original values from
            "population".

        combine_tables(individuals_table: param.reactive.rx) ->
        pn.widgets.Tabulator:
            Combines individuals and sample set data into a single table using
            pandas.merge.

        __panel__ -> pn.Column:
            The main content of the page, retrieved from `datastore.tsm.ts`.
            Updates options based on button interactions and returns a Column
            layout.

        options_sidebar() -> pn.Card:
            Creates a Panel card containing options for the individuals table:
                - Page size selector.
                - Sample set selector.

        modification_sidebar() -> pn.Column:
            Creates a Panel column containing data modification options:
                - Card with population from and sample set to selectors.
                - Restore and update buttons.
                - Warning message for invalid data.
    """

    sample_sets_table = param.ClassSelector(class_=SampleSetsTable)
    columns = [
        "color",
        "population",
        "sample_set_id",
        "name_sample_set",
        "name_individual",
        "longitude",
        "latitude",
        "selected",
    ]
    editors = {k: None for k in columns}
    editors["sample_set_id"] = {
        "type": "number",
        "valueLookup": True,
    }
    editors["selected"] = {
        "type": "list",
        "values": [False, True],
        "valuesLookup": True,
    }
    formatters = {
        "selected": {"type": "tickCross"},
        "color": {"type": "color"},
    }
    filters = {
        "name_individual": {
            "type": "input",
            "func": "like",
            "placeholder": "Enter name",
        },
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
        },
        "name_sample_set": {
            "type": "input",
            "func": "like",
            "placeholder": "Enter name",
        },
    }
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
    population_from = pn.widgets.Select(
        name="Original population ID",
        value=None,
        sizing_mode="stretch_width",
        description=("Reassign individuals with this population ID."),
    )
    sample_set_to = pn.widgets.Select(
        name="New sample set ID",
        value=None,
        sizing_mode="stretch_width",
        description=("Reassign individuals to this sample set ID."),
    )
    mod_update_button = pn.widgets.Button(
        name="Reassign",
        button_type="success",
        margin=(10, 10),
        description="Apply reassignment.",
    )
    refresh_button = pn.widgets.Button(
        name="Refresh",
        button_type="success",
        margin=(10, 0),
        description="Refresh to apply updates to entire page.",
    )
    restore_button = pn.widgets.Button(
        name="Restore",
        button_type="danger",
        margin=(10, 10),
        description="Restore sample sets to their original state.",
    )
    data_mod_warning = pn.pane.Alert(
        """Please enter a valid population ID and
        a non-negative new sample set ID""",
        alert_type="warning",
        visible=False,
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.table.set_index(["id"], inplace=True)
        self.data = self.param.table.rx()
        all_sample_set_ids = self.get_sample_set_ids()
        self.sample_select.options = all_sample_set_ids
        self.sample_select.value = all_sample_set_ids

    @property
    def tooltip(self) -> pn.widgets.TooltipIcon:
        """Returns a TooltipIcon widget containing information about the
        individuals table and how to edit it.

        Returns:
            pn.widgets.TooltipIcon: A TooltipIcon widget displaying
            information.
        """
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

    def sample_sets(self, only_selected: Optional[bool] = True):
        """Returns a dictionary with a sample set id to samples list mapping.

        Arguments:
            only_selected (bool, optional): If True, only considers
            individuals marked as selected in the table. Defaults to True.

        Returns:
            dict: A dictionary where keys are sample set IDs and values are
            lists of samples (tskit node IDs) belonging to that set. If
            `only_selected` is True, only samples marked as selected are
            included in the lists.
        """
        sample_sets = {}
        inds = self.data.rx.value
        for _, ind in inds.iterrows():
            if not ind.selected and only_selected:
                continue
            sample_set = ind.sample_set_id
            if sample_set not in sample_sets:
                sample_sets[sample_set] = []
            sample_sets[sample_set].extend(ind.nodes)
        return sample_sets

    def get_population_ids(self) -> List[int]:
        """Returns a sorted list of unique population IDs present in the data.

        Returns:
            list: A list containing all unique population IDs in the table.
        """
        return sorted(self.data.rx.value["population"].unique().tolist())

    def get_sample_set_ids(self) -> List[int]:
        """Returns a sorted list of unique sample set IDs present in the data.

        This method combines sample set IDs from two sources:

        1. Unique IDs from the "sample_set_id" column of the underlying data
           (self.data.rx.value).
        2. (Optional) IDs retrieved from the SampleSetsTable object
           (accessed through self.sample_sets_table) iff it is defined.

        Returns:
            list: A sorted list containing all unique sample set IDs found in
            the data and potentially from the `SampleSetsTable`.
        """
        individuals_sets = sorted(self.data.rx.value["sample_set_id"].tolist())
        if self.sample_sets_table is not None:  # Nonetype when not yet defined
            individuals_sets = (
                individuals_sets + self.sample_sets_table.get_ids()
            )
        return sorted(list(set(individuals_sets)))

    @property
    def sample2ind(self) -> Dict[int, int]:
        """Creates a dictionary that maps sample (tskit node) IDs to individual
        IDs.

        This method iterates through the underlying data and builds a
        dictionary where:
        Keys are sample (tskit node) IDs. Values are the corresponding
        individual IDs
        (indices) in the data.

        Returns:
            dict: A dictionary mapping sample (tskit node) IDs to their
            corresponding
            individual IDs.
        """
        inds = self.data.rx.value
        d = {}
        for index, ind in inds.iterrows():
            for node in ind.nodes:
                d[node] = index
        return d

    def samples(self):
        """Yields all sample (tskit node) IDs present in the data.

        This method iterates through the underlying data and yields each sample
        (tskit node) ID.

        Yields:
            int: Sample (tskit node) ID from the data.
        """

        for _, ind in self.data.rx.value.iterrows():
            for node in ind.nodes:
                yield node

    def loc(self, i: int) -> pd.core.series.Series:
        """Returns the individual data, pd.core.series.Series object, for a
        specific index (ID) i.

        Arguments:
            i (int): The index (ID) of the individual to retrieve.

        Returns:
            pd.core.series.Series: A pandas Series representing the individual
            data corresponding to the provided index.
        """
        return self.data.rx.value.loc[i]

    def reset_modification(self):
        """Resets the "sample_set_id" column of the underlying data
        (`self.data.rx.value`) back to the original values from the
        "population" column.

        This effectively undoes any modifications made to sample set
        assignments.
        """
        self.data.rx.value.sample_set_id = self.data.rx.value.population

    def combine_tables(
        self, individuals_table: param.reactive.rx
    ) -> pn.widgets.Tabulator:
        """Combines individuals data and sample set data into a single table.

        This method merges the data from two sources:

        1. The individuals data (`individuals_table.rx.value`) from the
        provided
           `individuals_table` argument.
        2. The sample set data (`self.sample_sets_table.data.rx.value`)
           from the `SampleSetsTable` object (accessed through
           `self.sample_sets_table`)
           if it's defined.

        The merge is performed using pandas.merge based on the
        "sample_set_id" column.
        The resulting table includes additional columns with suffixes
        indicating their
        origin (e.g., "_individual" for data from `individuals_table`).

        Arguments:
            individuals_table (aram.reactive.rx object):
                An object containing the individuals data table.

        Returns:
            pn.widgets.Tabulator:
                A Tabulator widget representing the combined individuals and
                sample set data.
        """

        combined_df = pd.merge(
            individuals_table.rx.value,
            self.sample_sets_table.data.rx.value,
            left_on="sample_set_id",
            right_index=True,
            suffixes=("_individual", "_sample_set"),
        )

        combined_df["id"] = combined_df.index
        combined_df = combined_df[self.columns]

        combined_table = pn.widgets.Tabulator(
            combined_df,
            pagination="remote",
            layout="fit_columns",
            selectable=True,
            page_size=self.page_size,
            formatters=self.formatters,
            editors=self.editors,
            sorters=[
                {"field": "id", "dir": "asc"},
                {"field": "selected", "dir": "des"},
            ],
            margin=10,
            text_align={col: "right" for col in self.columns},
            header_filters=self.filters,
        )
        return combined_table

    @pn.depends(
        "page_size",
        "sample_select.value",
        "mod_update_button.value",
        "refresh_button.value",
        "restore_button.value",
        "sample_sets_table.create_sample_set_button.value",
    )
    def __panel__(self) -> pn.Column:
        """Returns the main content of the page which is retrieved from the
        `datastore.tsm.ts` attribute.

        Returns:
            pn.Column: The layout for the main content area.
        """
        self.population_from.options = self.get_population_ids()
        all_sample_set_ids = self.get_sample_set_ids()
        self.sample_set_to.options = all_sample_set_ids
        self.sample_select.options = all_sample_set_ids

        if isinstance(self.sample_select.value, list):
            self.data.rx.value["selected"] = False
            for sample_set_id in self.sample_select.value:
                self.data.rx.value.loc[
                    self.data.rx.value.sample_set_id == sample_set_id,
                    "selected",
                ] = True
        if (
            isinstance(self.mod_update_button.value, bool)
            and self.mod_update_button.value
        ):
            self.table.loc[
                self.table["population"] == self.population_from.value,  # pyright: ignore[reportIndexIssue]
                "sample_set_id",
            ] = self.sample_set_to.value

        if (
            isinstance(self.restore_button.value, bool)
            and self.restore_button.value
        ):
            self.reset_modification()

        data = self.data

        table = self.combine_tables(data)

        return pn.Column(pn.Row(self.tooltip, align=("start", "end")), table)

    def options_sidebar(self) -> pn.Card:
        """Creates a Panel card containing options for the individuals table.

        Returns:
            pn.Card: A Panel card containing the following options:
                - Page size selector: Allows the user to adjust the number of
                rows per page.
                - Sample set selector: Allows the user to select specific
                sample sets to filter the data.
        """
        return pn.Card(
            self.param.page_size,
            self.sample_select,
            collapsed=False,
            title="Individuals table options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )

    def modification_sidebar(self) -> pn.Column:
        """Creates a Panel column containing the data modification options.

        Returns:
            pn.Column: A Panel column containing the following elements:
                - A card with the following options:
                    - Population from selector: Allows the user to select the
                      original population ID.
                    - Sample set to selector: Allows the user to select the
                      new sample set ID.
                    - Restore button: Resets modifications.
                    - Update button: Applies the modifications.
                - A warning message (`self.data_mod_warning`) that is displayed
                  when invalid data is entered.
        """
        modification_header = pn.pane.HTML(
            "<h4 style='margin: 0;'>Batch reassign individuals</h4>"
        )
        return pn.Column(
            pn.Card(
                modification_header,
                pn.Row(self.population_from, self.sample_set_to),
                pn.Row(
                    pn.Spacer(width=120),
                    self.restore_button,
                    self.mod_update_button,
                    align="end",
                ),
                collapsed=False,
                title="Data modification",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.data_mod_warning,
        )


class DataStore(Viewer):
    """Class representing a data store for managing and accessing data used for
    analysis. This class provides access to various data sources and
    functionalities related to individuals, sample sets, and the underlying
    TreeSequenceModel.

    Attributes:
        tsm (param.ClassSelector):
            ClassSelector for the model.TSModel object holding the TreeSequence
              data.
        sample_sets_table (param.ClassSelector):
            ClassSelector for the SampleSetsTable object managing sample set
            information.
        individuals_table (param.ClassSelector):
            ClassSelector for the IndividualsTable object handling individual
            data and filtering.
        views (param.List, constant=True):
            A list of views to be displayed.

    Methods:
        color(self) -> pd.core.series.Series:
            Returns a pandas DataFrame containing the colors of selected
            individuals
            merged with their corresponding sample set names.

        haplotype_gnn(self, focal_ind, windows=None):
            Calculates and returns the haplotype Genealogical Nearest
            Neighbors (GNN)
            for a specified focal individual and optional window sizes.
    """

    tsm = param.ClassSelector(class_=model.TSModel)
    sample_sets_table = param.ClassSelector(class_=SampleSetsTable)
    individuals_table = param.ClassSelector(class_=IndividualsTable)

    views = param.List(constant=True)

    @property
    def color(self) -> pd.core.series.Series:
        """Return colors of selected individuals."""
        color = pd.merge(
            self.individuals_table.data.rx.value,
            self.sample_sets_table.data.rx.value,
            left_on="sample_set_id",
            right_index=True,
        )
        return color.loc[color.selected].color

    def haplotype_gnn(
        self, focal_ind: int, windows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """Calculates and returns the haplotype Genealogical Nearest Neighbors
        (GNN) for a specified focal individual and optional window sizes.

        Arguments:
            focal_ind (int): The index (ID) of the focal individual within the
                individuals table.
            windows (List[int], optional): A list of window sizes for
            calculating
                GNNs within those specific windows. If None, GNNs are
                calculated
                across the entire sequence length.

        Returns:
            pandas.DataFrame: A DataFrame containing GNN information for each
            haplotype.
        """
        sample_sets = self.individuals_table.sample_sets()
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


def make_individuals_table(tsm: model.TSModel) -> IndividualsTable:
    """Creates an IndividualsTable object from the data in the provided TSModel
    object, by iterating through the individuals in the tree sequence and
    creates an Individual object for each one, creating a Pandas DataFrame
    populated with the individual level information.

    Arguments:
        tsm (model.TSModel): The TSModel object containing the tree
        sequence data.

    Returns:
        IndividualsTable: An IndividualsTable object populated with
        individual level information from the tree sequence.
    """
    result = []
    for ts_ind in tsm.ts.individuals():
        ind = Individual(individual=ts_ind)
        result.append(ind)
    return IndividualsTable(table=pd.DataFrame(result))


def make_sample_sets_table(tsm: model.TSModel) -> SampleSetsTable:
    """Creates a SampleSetsTable object from the data in the provided TSModel
    object, by iterating through the populations in the tree sequence and
    creates a SampleSet object for each one, creating a Pandas DataFrame
    populated with the population level information.

    Arguments:
        tsm (model.TSModel): The TSModel object containing the tree
        sequence data.

    Returns:
        SampleSet: A SampleSet object populated with
        population level information from the tree sequence.
    """
    result = []
    for ts_pop in tsm.ts.populations():
        ss = SampleSet(
            sample_set_id=ts_pop.id, population=ts_pop, predefined=True
        )
        result.append(ss)
    return SampleSetsTable(table=pd.DataFrame(result))


def preprocess(tsm: model.TSModel) -> Tuple[IndividualsTable, SampleSetsTable]:
    """Take a TSModel and creates IndividualsTable and SampleSetsTable objects
    from the data in the provided TSModel object.

    Arguments:
        tsm (model.TSModel): The TSModel object containing the tree sequence
        data.

    Returns:
        Tuple[IndividualsTable, SampleSetsTable]: A tuple containing two
        elements:
            IndividualsTable: An IndividualsTable object populated with
            individual
            information from the tree sequence.
            SampleSetsTable: A SampleSetsTable object populated with population
            information from the tree sequence.
    """
    logger.info(
        "Preprocessing data: making individuals and sample sets tables"
    )
    sample_sets_table = make_sample_sets_table(tsm)
    individuals_table = make_individuals_table(tsm)
    return individuals_table, sample_sets_table
