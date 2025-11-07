"""Mixin classes"""

import panel as pn
from panel.viewable import Viewer


class TooltipMixin(Viewer):
    _tooltip = None

    @property
    def tooltip(self) -> pn.widgets.TooltipIcon:
        return pn.widgets.TooltipIcon(value=self._tooltip)


class SampleSelectWarningMixin(Viewer):
    _min_sample_sets = 1

    def sample_select_warning(self) -> pn.pane.Alert:
        return pn.pane.Alert(
            (
                f"Select at least {self._min_sample_sets} sample set to see "
                "this plot. Sample sets are selected on the Individuals page"
            ),
            alert_type="warning",
        )


class MultiSampleSelectWarningMixin(SampleSelectWarningMixin):
    _min_sample_sets = 2
