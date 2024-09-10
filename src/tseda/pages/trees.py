"""Module to plot local trees

TODO:

- fix bounds of position / treeid parameters
- add more options to style tree
- add index parameter to select tree by index - needs to be mutually
  exclusive with position parameter
"""

import ast

import holoviews as hv
import panel as pn
import param

hv.extension("bokeh")


def eval_options(options):
    """Evaluate options parameter."""
    return ast.literal_eval(options)


class Tree(param.Parameterized):
    # treeid = param.Integer(default=0, bounds=(0, None), doc="Get
    # tree by zero-based index")
    position = param.Integer(
        default=1, bounds=(1, None), doc="Get tree at genome position (bp)"
    )
    width = param.Integer(default=800, doc="Width of the tree plot")
    height = param.Integer(default=800, doc="Height of the tree plot")
    options = param.String(
        default="{'y_axis': 'time', 'node_labels': {}}",
        doc=(
            "Additional options for configuring tree plot. "
            "Must be a valid dictionary string."
        ),
    )

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self._tree = self.tsm.ts.first()

    @property
    def default_css(self):
        """Default css styles for tree nodes"""
        styles = []
        for ss in self.tsm.sample_sets:
            s = f".node.p{ss.id} > .sym " + "{" + f"fill: {ss.color}" + "}"
            styles.append(s)
        css_string = " ".join(styles)
        return css_string

    @property
    def tree(self):
        self._tree = self.tsm.ts.at(self.position)
        return self._tree

    @param.depends("width", "height", "position", "options")
    def plot(self):
        options = eval_options(self.options)
        return pn.pane.HTML(
            self.tree.draw_svg(
                size=(self.width, self.height),
                style=self.default_css,
                **options,
            )
        )


def page(tsm):
    tree = Tree(tsm)
    return pn.Row(
        pn.Param(tree.param, width=300),
        tree.plot,
    )
