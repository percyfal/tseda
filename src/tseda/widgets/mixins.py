"""Mixin classes"""

import panel as pn
from panel.viewable import Viewer


class TooltipMixin(Viewer):
    _tooltip = None

    @property
    def tooltip(self) -> pn.widgets.TooltipIcon:
        return pn.widgets.TooltipIcon(value=self._tooltip)
