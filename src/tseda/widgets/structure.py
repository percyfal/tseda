"""Structure widgets"""

import colorcet as cc

from .base import BaseFigure
from .mixins import MultiSampleSelectWarningMixin
from .views import FstMixin, IndividualGNNMixin, MeanGNNMixin


class IndividualGNNFigure(BaseFigure, IndividualGNNMixin):
    """Make a plot of all individual GNN outputs."""

    def __panel__(self):
        p = self.data.hvplot.heatmap(cmap=cc.bgy, height=300, responsive=True)
        return p


class MeanGNNFigure(BaseFigure, MeanGNNMixin):
    """Make a plot of mean GNN outputs."""

    def __panel__(self):
        p = self.data.hvplot.heatmap(cmap=cc.bgy, height=300, responsive=True)
        return p


class FstFigure(BaseFigure, FstMixin, MultiSampleSelectWarningMixin):
    """Make a plot of Fst between sample sets."""

    _min_sample_sets = 2

    def __panel__(self):
        p = self.data.hvplot.heatmap(cmap=cc.bgy, height=300, responsive=True)
        return p
