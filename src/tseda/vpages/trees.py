"""Module to plot local trees

TODO:

- fix bounds of position / treeid parameters
"""

import ast

import holoviews as hv
import panel as pn
import param

from tseda import config

from .core import View

hv.extension("bokeh")


def eval_options(options):
    """Evaluate options parameter."""
    return ast.literal_eval(options)


class Tree(View):
    search_by = pn.widgets.ToggleGroup(
        name="Search By",
        options=["Position", "Tree Index"],
        behavior="radio",
        button_type="primary",
    )

    tree_index = param.Integer(default=0, doc="Get tree by zero-based index")
    position = param.Integer(
        default=None, doc="Get tree at genome position (bp)"
    )

    warning_pane = pn.pane.Alert(
        "The input for position or tree index is out of bounds.",
        alert_type="warning",
        visible=False,
    )

    width = param.Integer(default=750, doc="Width of the tree plot")
    height = param.Integer(default=520, doc="Height of the tree plot")
    options = param.String(
        default="{'y_axis': 'time', 'node_labels': {}}",
        doc=(
            "Additional options for configuring tree plot. "
            "Must be a valid dictionary string."
        ),
    )
    next = param.Action(
        lambda x: x.next_tree(), doc="Next tree", label="Next tree"
    )
    prev = param.Action(
        lambda x: x.prev_tree(), doc="Previous tree", label="Previous tree"
    )

    symbol_size = param.Number(default=8, bounds=(0, None), doc="Symbol size")

    def next_tree(self):
        self.position = None
        self.tree_index = min(
            self.datastore.tsm.ts.num_trees - 1, int(self.tree_index) + 1
        )
        # pyright: ignore[reportOperatorIssue]

    def prev_tree(self):
        self.position = None
        self.tree_index = max(0, int(self.tree_index) - 1)
        # pyright: ignore[reportOperatorIssue]

    @property
    def default_css(self):
        """Default css styles for tree nodes"""
        styles = []
        sample_sets = self.datastore.sample_sets_table.data.rx.value
        individuals = self.datastore.individuals_table.data.rx.value
        sample2ind = self.datastore.individuals_table.sample2ind
        for n in self.datastore.individuals_table.samples():
            ssid = individuals.loc[sample2ind[n]].sample_set_id
            ss = sample_sets.loc[ssid]
            s = f".node.n{n} > .sym " + "{" + f"fill: {ss.color} " + "}"
            styles.append(s)
        css_string = " ".join(styles)
        return css_string

    @param.depends("position", "tree_index", watch=True)
    def check_inputs(self):
        if self.position is not None and (
            int(self.position) < 0
            or int(self.position) > self.datastore.tsm.ts.sequence_length
        ):
            self.warning_pane.visible = True
            raise ValueError
        if (
            self.tree_index is not None
            and int(self.tree_index) < 0
            or int(self.tree_index) > self.datastore.tsm.ts.num_trees
        ):
            self.warning_pane.visible = True
            raise ValueError
        else:
            self.warning_pane.visible = False

    @param.depends(
        "width", "height", "position", "options", "symbol_size", "tree_index"
    )
    def __panel__(self):
        options = eval_options(self.options)
        if self.position is not None:
            tree = self.datastore.tsm.ts.at(self.position)
            self.tree_index = tree.index
        else:
            tree = self.datastore.tsm.ts.at_index(self.tree_index)
        pos1 = int(tree.get_interval()[0])
        pos2 = int(tree.get_interval()[1]) - 1
        return pn.Column(
            pn.pane.Markdown(
                f"## Tree index {self.tree_index} (position {pos1} - {pos2})"
            ),
            pn.pane.HTML(
                tree.draw_svg(
                    size=(self.width, self.height),
                    symbol_size=self.symbol_size,
                    style=self.default_css,
                    **options,
                ),
            ),
            pn.Row(
                self.param.prev,
                self.param.next,
            ),
        )

    def update_sidebar(self):
        """Dynamically update the sidebar based on searchBy value."""
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
                self.param.options,
                self.param.symbol_size,
                collapsed=False,
                title="Tree plotting options",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
            self.warning_pane,
        )
        return sidebar_content

    @param.depends("search_by.value", watch=True)
    def sidebar(self):
        return self.update_sidebar()


class TreesPage(View):
    key = "trees"
    title = "Trees"
    data = param.ClassSelector(class_=Tree)

    def __init__(self, **params):
        super().__init__(**params)
        self.data = Tree(datastore=self.datastore)
        self.sample_sets = self.datastore.sample_sets_table

    def __panel__(self):
        return pn.Column(
            self.data,
        )

    def sidebar(self):
        return pn.Column(
            self.data.sidebar,
            self.sample_sets.sidebar_table,
        )
