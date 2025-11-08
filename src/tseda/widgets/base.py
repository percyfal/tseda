"""Base widget classes."""

from dataclasses import dataclass

import param
from panel.viewable import Viewer

from tseda.datastore import DataStore
from tseda.windows import make_windows


@dataclass
class FontSize:
    name: str
    unit: str
    size: int

    def __str__(self):
        return f"{self.size}{self.unit}"


@dataclass
class FontSizes:
    base_font_size: int
    font_scale: float
    unit: str

    def __post_init__(self):
        self.tiny = FontSize("tiny", self.unit, int(self.base_font_size * 0.6))
        self.scriptsize = FontSize(
            "scriptsize", self.unit, int(self.base_font_size * 0.75)
        )
        self.small = FontSize(
            "small", self.unit, int(self.base_font_size * 0.875)
        )
        self.normal = FontSize("normal", self.unit, self.base_font_size)
        self.large = FontSize(
            "large", self.unit, int(self.base_font_size * 1.25)
        )
        self.big = FontSize("big", self.unit, int(self.base_font_size * 1.5))
        self.huge = FontSize("huge", self.unit, int(self.base_font_size * 2.0))


# TODO: should the base view only concern itself with data
# transformations and defer viz to Figure classes?
class BaseView(Viewer):
    key = param.String()
    title = param.String()

    def __init__(self, *, datastore: DataStore, **params):
        super().__init__(**params)
        self.datastore = datastore


class BaseFigure(BaseView):
    width = param.Integer(
        default=800,
        doc="Figure width",
    )
    height = param.Integer(
        default=400,
        doc="Figure height",
    )
    base_font_size = param.Integer(default=12, doc="Base font size")
    font_scale = param.Number(
        default=1.0,
        doc="Font scaling factor",
        bounds=(0.1, 10.0),
    )
    font_unit = param.String(
        default="pt",
        doc="Font size unit",
    )
    sizing_mode = param.String(
        default=None,
        doc="Sizing mode",
    )
    show_legend = param.Boolean(
        default=True,
        doc="Show legend",
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.font_sizes = FontSizes(
            self.base_font_size, self.font_scale, self.font_unit
        )


class WindowedFigure(BaseFigure):
    window_size = param.Integer(
        default=10000,
        bounds=(1, None),
        doc="""Size of the sliding window to use for statistics.""",
    )

    def __init__(self, **params):
        super().__init__(**params)

    def make_windows(self):
        return make_windows(
            self.window_size, self.datastore.tsm.ts.sequence_length
        )
