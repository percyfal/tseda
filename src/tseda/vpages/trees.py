"""Tree page structure.

This is a module to plot local trees.

TODO:
- fix bounds of position / treeid parameters
"""

import ast
from typing import Tuple, Union

import holoviews as hv
import panel as pn
import param
import tskit

from tseda import config

from .core import View

hv.extension("bokeh")


def eval_options(options: str) -> dict:
    """Converts the option string to a dictionary.

    Args:
    options (str): The options inputted by the user.

    Returns:
    dict: A dictionary containing the options.
    """
    return ast.literal_eval(options)


class Tree(View):
    """This class represents a panel component for visualizing tskit trees.

    Attributes:
        search_by (pn.widgets.ToggleGroup): Select the method for searching
        for trees.
        tree_index (param.Integer): Get tree by zero-based index.
        position (param.Integer): Get tree at genome position (bp).
        position_index_warning (pn.pane.Alert): Warning message displayed
        when position or tree index is invalid.
        width (param.Integer): Width of the tree plot.
        height (param.Integer): Height of the tree plot.
        num_trees (pn.widgets.Select): Select the number of trees to display.
        y_axis (pn.widgets.Checkbox): Toggle to include y-axis in the plot.
        y_ticks (pn.widgets.Checkbox): Toggle to include y-axis ticks in the
        plot.
        x_axis (pn.widgets.Checkbox): Toggle to include x-axis in the plot.
        sites_mutations (pn.widgets.Checkbox): Toggle to clude sites and
        mutations
        in the plot.
        pack_unselected (pn.widgets.Checkbox): Toggle to pack unselected
        sample sets
        in the plot.
        options_doc (pn.widgets.TooltipIcon): Tooltip explaining advanced
        options.
        symbol_size (param.Number): Size of the symbols representing tree
        nodes.
        node_labels (param.String): Dictionary specifying custom labels for
        tree nodes.
        additional_options (param.String): Dictionary specifying additional
        plot options.
        advanced_warning (pn.pane.Alert): Warning message displayed when
        advanced options
        are invalid.
        next (param.Action): Action triggered by the "Next tree" button.
        prev (param.Action): Action triggered by the "Previous tree" button.
        slider (pn.widgets.IntSlider): Slider for selecting chromosome
        position.

    Methods:
        __init__(self, **params): Initializes the `Tree` class with provided
        parameters.
        default_css(self): Generates default CSS styles for tree nodes.
        next_tree(self): Increments the tree index to display the next tree.
        prev_tree(self): Decrements the tree index to display the previous
        tree.
        check_inputs(self): Raises a ValueError if position or tree index is
        invalid.
        handle_advanced(self): Processes advanced  options for plotting.
        update_slider(self): Updates the slider value based on the selected
        position.
        update_position(self): Updates the position based on the slider value.
        plot_tree(self, tree, omit_sites, y_ticks, node_labels,
        additional_options): Generates
        the HTML plot for a single tree with specified options.
        get_all_trees(self, trees): Constructs a panel layout displaying all
        provided trees.
        multiple_trees(self): Adjusts layout and options for displaying
        multiple trees.
        advanced_options(self): Defines the layout for the advanced options
        in the sidebar.
        __panel__(self): Defines the layout of the main content on the page.
        update_sidebar(self): Created the sidebar based on the chosen search
        method.
        sidebar(self): Calls the update_sidebar method whenever chosen search
        method changes.
    """

    search_by = pn.widgets.ToggleGroup(
        name="Search By",
        options=["Position", "Tree Index"],
        behavior="radio",
        button_type="primary",
    )

    tree_index = param.Integer(
        default=0,
        doc="""Get tree by zero-based index. If multiple trees are
        shown, this is the index of the first tree.""",
    )
    position = param.Integer(
        default=None,
        doc="""Get tree at genome position (bp). If multiple trees are
        shown, this is the position of the first tree.""",
    )

    position_index_warning = pn.pane.Alert(
        """The input for position or tree index is
        out of bounds for the specified number
        of trees.""",
        alert_type="warning",
        visible=False,
    )

    width = param.Integer(default=750, doc="Width of the tree plot")
    height = param.Integer(default=520, doc="Height of the tree plot")

    num_trees = pn.widgets.Select(
        name="Number of trees",
        options=[1, 2, 3, 4, 5, 6],
        value=1,
        description="""Select the number of trees to display. The first tree
        will represent your selected chromosome position or tree index.""",
    )

    y_axis = pn.widgets.Checkbox(name="Include y-axis", value=True)
    y_ticks = pn.widgets.Checkbox(name="Include y-ticks", value=True)
    x_axis = pn.widgets.Checkbox(name="Include x-axis", value=False)
    sites_mutations = pn.widgets.Checkbox(
        name="Include sites and mutations", value=True
    )
    pack_unselected = pn.widgets.Checkbox(
        name="Pack unselected sample sets", value=False, width=197
    )
    options_doc = pn.widgets.TooltipIcon(
        value=(
            """Select various elements to include in your graph.
            Pack unselected sample sets: Selecting this option
            will allow large polytomies involving unselected
            samples to be summarised as a dotted line. Selection
            of samples and sample sets can be done on the
            Individuals page."""
        ),
    )

    symbol_size = param.Number(default=8, bounds=(0, None), doc="Symbol size")

    node_labels = param.String(
        default="{}",
        doc=(
            """Show custom labels for the nodes (specified by ID).
            Any nodes not present will not have a label.
            Examle: {1: 'label1', 2: 'label2',...}"""
        ),
    )
    additional_options = param.String(
        default="{}",
        doc=(
            """Add more options as specified by the documentation.
            Must be a valid dictionary.
            Examle: {'title': 'My Tree',...}"""
        ),
    )

    advanced_warning = pn.pane.Alert(
        "The inputs for the advanced options are not valid.",
        alert_type="warning",
        visible=False,
    )

    next = param.Action(
        lambda x: x.next_tree(), doc="Next tree", label="Next tree"
    )
    prev = param.Action(
        lambda x: x.prev_tree(), doc="Previous tree", label="Previous tree"
    )

    slider = pn.widgets.IntSlider(name="Chromosome Position")

    def __init__(self, **params):
        super().__init__(**params)
        self.slider.end = int(self.datastore.tsm.ts.sequence_length - 1)

    @property
    def default_css(self) -> str:
        """Default css styles for tree nodes.

        Returns:
            str: A string with the css styling.
        """
        styles = []
        sample_sets = self.datastore.sample_sets_table.data.rx.value
        individuals = self.datastore.individuals_table.data.rx.value
        sample2ind = self.datastore.individuals_table.sample2ind
        selected_sample_sets = self.datastore.individuals_table.sample_sets()
        selected_samples = [
            int(i)
            for sublist in list(selected_sample_sets.values())
            for i in sublist
        ]
        for n in self.datastore.individuals_table.samples():
            ssid = individuals.loc[sample2ind[n]].sample_set_id
            ss = sample_sets.loc[ssid]
            if n in selected_samples:
                s = (
                    f".node.n{n} > .sym "
                    + "{"
                    + f"fill: {ss.color}; stroke: black; stroke-width: 2px;"
                    + "}"
                )
            else:
                s = f".node.n{n} > .sym " + "{" + f"fill: {ss.color} " + "}"
            styles.append(s)
        css_string = " ".join(styles)
        return css_string

    def next_tree(self):
        """Increments the tree index to display the next tree."""
        self.position = None
        self.tree_index = min(
            self.datastore.tsm.ts.num_trees - self.num_trees.value,
            int(self.tree_index) + 1,
        )  # pyright: ignore[reportOperatorIssue]

    def prev_tree(self):
        """Decrements the tree index to display the previous tree."""
        self.position = None
        self.tree_index = max(0, int(self.tree_index) - 1)  # pyright: ignore[reportOperatorIssue]

    def check_inputs(self):
        """Checks the inputs for position and tree index.

        Raises
            ValueError: If the position or tree index is invalid.
        """
        if self.position is not None:
            if (
                int(self.position) < 0
                or int(self.position) >= self.datastore.tsm.ts.sequence_length
            ):
                raise ValueError
            elif int(
                self.datastore.tsm.ts.at(self.position).index
                + self.num_trees.value
            ) > int(self.datastore.tsm.ts.num_trees):
                raise ValueError
        if self.tree_index is not None and (
            int(self.tree_index) < 0
            or int(self.tree_index) + int(self.num_trees.value)
            > self.datastore.tsm.ts.num_trees
        ):
            raise ValueError
        else:
            self.position_index_warning.visible = False

    def handle_advanced(self) -> Tuple[bool, Union[dict, None]]:
        """Handles advanced options so that they are returned in the correct
        format.

        Returns
            bool: Whether mutations & sites should be included in the tree.
            Union[dict, None]: Specified the option for ticks on the y-axis.
        """
        if self.sites_mutations.value is True:
            omit_sites = not self.sites_mutations.value
        else:
            omit_sites = True
        if self.y_ticks.value is True:
            y_ticks = None
        else:
            y_ticks = {}
        if self.node_labels == "":
            self.node_labels = "{}"
        if self.additional_options == "":
            self.additional_options = "{}"
        return omit_sites, y_ticks

    @param.depends("position", watch=True)
    def update_slider(self):
        """Updates the slider value based on the selected position."""
        if self.position is not None:
            self.slider.value = self.position

    @param.depends("slider.value_throttled", watch=True)
    def update_position(self):
        """Updates the position based on the slider value."""
        self.position = self.slider.value

    def plot_tree(
        self,
        tree: tskit.trees.Tree,
        omit_sites: bool,
        y_ticks: Union[None, dict],
        node_labels: dict,
        additional_options: dict,
    ) -> Union[pn.Accordion, pn.Column]:
        """Plots a single tree.

        Arguments:
            tree (tskit.trees.Tree): The tree to be plotted.
            omit_sites (bool): If sites & mutaions should be included in the
            plot.
            y_ticks (Union[None, dict]): If y_ticks should be included in the
            plot.
            nodel_labels (dict): Any customised node labels.
            additional_options (dict): Any additional plotting options.

        Returns:
            Union[pn.Accordion, pn.Column]: A panel element containing the
            tree.
        """
        try:
            plot = tree.draw_svg(
                size=(self.width, self.height),
                symbol_size=self.symbol_size,
                y_axis=self.y_axis.value,
                x_axis=self.x_axis.value,
                omit_sites=omit_sites,
                node_labels=node_labels,
                y_ticks=y_ticks,
                pack_untracked_polytomies=self.pack_unselected.value,
                style=self.default_css,
                **additional_options,
            )
            self.advanced_warning.visible = False
        except (ValueError, SyntaxError, TypeError):
            plot = tree.draw_svg(
                size=(self.width, self.height),
                y_axis=True,
                node_labels={},
                style=self.default_css,
            )
            self.advanced_warning.visible = True
        pos1 = int(tree.get_interval()[0])
        pos2 = int(tree.get_interval()[1]) - 1
        if int(self.num_trees.value) > 1:
            return pn.Accordion(
                pn.Column(
                    pn.pane.HTML(plot),
                    name=f"Tree index {tree.index} (position {pos1} - {pos2})",
                ),
                active=[0],
            )
        else:
            return pn.Column(
                pn.pane.HTML(
                    f"<h2>Tree index {tree.index}"
                    f" (position {pos1} - {pos2})</h2>",
                    sizing_mode="stretch_width",
                ),
                pn.pane.HTML(plot),
            )

    def get_all_trees(self, trees: list) -> Union[None, pn.Column]:
        """Returns all trees in columns and rows.

        Arguments:
            trees: A list of all trees to be displayed.

        Returns:
            Union[None, pn.Column]: A column of rows with trees,
            if there are any trees to display.
        """
        if not trees:
            return None
        rows = [pn.Row(*trees[i : i + 2]) for i in range(0, len(trees), 2)]
        return pn.Column(*rows)

    @param.depends("num_trees.value", watch=True)
    def multiple_trees(self):
        """Sets the default setting depending on if one or several trees are
        displayed."""
        if int(self.num_trees.value) > 1:
            self.width = 470
            self.height = 470
            self.y_axis.value = False
            self.x_axis.value = False
            self.y_ticks.value = False
            self.sites_mutations.value = False
            self.pack_unselected.value = True
            self.symbol_size = 6
        else:
            self.width = 750
            self.height = 520
            self.y_axis.value = True
            self.x_axis.value = False
            self.y_ticks.value = True
            self.sites_mutations.value = True
            self.pack_unselected.value = False
            self.symbol_size = 8

    def advanced_options(self):
        """Defined the content of the advanced options card in the sidebar."""
        doc_link = (
            "https://tskit.dev/tskit/docs/"
            "stable/python-api.html#tskit.TreeSequence.draw_svg"
        )
        sidebar_content = pn.Column(
            pn.Card(
                pn.pane.HTML(
                    f"""<b>See the <a
                    href={doc_link}>
                    tskit documentation</a> for more information
                    about these plotting options.<b>"""
                ),
                self.num_trees,
                pn.Row(pn.pane.HTML("Options", width=30), self.options_doc),
                self.x_axis,
                self.y_axis,
                self.y_ticks,
                self.sites_mutations,
                self.pack_unselected,
                self.param.symbol_size,
                self.param.node_labels,
                self.param.additional_options,
                collapsed=True,
                title="Advanced plotting options",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.advanced_warning,
        )
        return sidebar_content

    @param.depends(
        "width",
        "height",
        "position",
        "symbol_size",
        "tree_index",
        "num_trees.value",
        "y_axis.value",
        "y_ticks.value",
        "x_axis.value",
        "sites_mutations.value",
        "pack_unselected.value",
        "node_labels",
        "additional_options",
        "slider.value_throttled",
    )
    def __panel__(self) -> pn.Column:
        """Returns the main content of the Trees page.

        Returns:
            pn.Column: The layout for the main content area.

        Raises:
            ValueError: If inputs are not in the correct format
        """
        try:
            self.check_inputs()
        except ValueError:
            self.position_index_warning.visible = True
            raise ValueError("Inputs for position or tree index are not valid")

        sample_sets = self.datastore.individuals_table.sample_sets()
        selected_samples = [
            int(i) for sublist in list(sample_sets.values()) for i in sublist
        ]
        if len(selected_samples) < 1:
            self.pack_unselected.value = False
            self.pack_unselected.disabled = True
        else:
            self.pack_unselected.disabled = False
        omit_sites, y_ticks = self.handle_advanced()
        try:
            node_labels = eval_options(self.node_labels)
            additional_options = eval_options(self.additional_options)
        except (ValueError, SyntaxError, TypeError):
            node_labels = None
            additional_options = None
            self.advanced_warning.visible = True
        trees = []
        for i in range(self.num_trees.value):
            if self.position is not None:
                tree = self.datastore.tsm.ts.at(self.position)
                self.tree_index = tree.index
                tree = self.datastore.tsm.ts.at_index(
                    (tree.index + i), tracked_samples=selected_samples
                )
            else:
                tree = self.datastore.tsm.ts.at_index(
                    int(self.tree_index) + i, tracked_samples=selected_samples
                )
                self.slider.value = int(tree.get_interval()[0])
            trees.append(
                self.plot_tree(
                    tree, omit_sites, y_ticks, node_labels, additional_options
                )
            )
        all_trees = self.get_all_trees(trees)
        return pn.Column(
            all_trees,
            pn.pane.Markdown(
                """**Tree plot** - Lorem Ipsum...
            Selected samples are marked with a black outline."""
            ),
            self.slider,
            pn.Row(
                self.param.prev,
                self.param.next,
            ),
        )

    def update_sidebar(self) -> pn.Column:
        """Renders the content of the sidebar based on searchBy value.

        Returns:
            pn.Column: The sidebar content.
        """
        if self.search_by.value == "Tree Index":
            self.position = None
            fields = [self.param.tree_index]
        else:
            fields = [self.param.position]

        sidebar_content = pn.Column(
            pn.Card(
                self.search_by,
                *fields,
                self.param.width,
                self.param.height,
                collapsed=False,
                title="Tree plotting options",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.position_index_warning,
        )
        return sidebar_content

    @param.depends("search_by.value", watch=True)
    def sidebar(self) -> pn.Column:
        """Makes sure the sidebar is updated whenever the search-by value is
        toggled.

        Returns:
            pn.Column: The sidebar content.
        """
        return self.update_sidebar()


class TreesPage(View):
    """Represents the trees page of the tseda application.

    Attributes:
        key (str): A unique identifier for this view within the application.
        title (str): The title displayed on the page.
        data (param.ClassSelector): The main content of the page.

    Methods:
        __init__(self, **params): Initializes the `TreesPage` class with
        provided parameters.
        __panel__() -> pn.Column: Defines the layout of the main content area.
        sidebar() -> pn.Column: Defines the layout of the sidebar content area.
    """

    key = "trees"
    title = "Trees"
    data = param.ClassSelector(class_=Tree)

    def __init__(self, **params):
        super().__init__(**params)
        self.data = Tree(datastore=self.datastore)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self):
        """Returns the main content of the page.

        Returns:
            pn.Column: The layout for the main content area.
        """
        return pn.Column(
            self.data,
        )

    def sidebar(self):
        """Returns the content of the sidebar.

        Returns:
            pn.Column: The layout for the sidebar.
        """
        return pn.Column(
            pn.pane.HTML(
                "<h2 style='margin: 0;'>Trees</h2>",
                sizing_mode="stretch_width",
            ),
            pn.pane.Markdown(
                (
                    "This section allows you to explore local genealogical "
                    "trees.<br><br>"
                    "Use the controls below to customize the plots and adjust"
                    "parameters."
                ),
                sizing_mode="stretch_width",
            ),
            self.data.sidebar,
            self.data.advanced_options,
            self.sample_sets.sidebar_table,
        )
