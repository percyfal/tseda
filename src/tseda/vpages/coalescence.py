"""Module to plot coalescence rates"""

import itertools

import numpy as np
import pandas as pd
import panel as pn
import param

from tseda import config

from .core import View, make_windows


class CoalescenceHeatmap(View):
    num_time_bins = param.Integer(
        default=100, bounds=(1, None), doc="Number of time bins"
    )
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Window size"
    )

    @param.depends("num_time_bins", "window_size")
    def __panel__(self):
        tsm = self.datastore.tsm
        samples, sample_sets = self.datastore.individuals_table.sample_sets()
        n_sample_sets = len(sample_sets)
        indexes = list(
            itertools.product(
                np.arange(n_sample_sets), np.arange(n_sample_sets)
            )
        )
        names = [
            self.datastore.sample_sets_table.names[i]
            for i in sample_sets.keys()
        ]
        pairs = list(itertools.product(names, names))
        time_intervals = np.logspace(
            0, np.log10(tsm.ts.max_time), self.num_time_bins
        )
        time_intervals = np.concatenate(([0], time_intervals, [np.inf]))
        genome_intervals = make_windows(
            self.window_size, tsm.ts.sequence_length
        )
        rates = pd.DataFrame(
            tsm.ts.pair_coalescence_rates(
                time_windows=time_intervals, windows=genome_intervals
            ).T
        )
        hm = rates.hvplot.heatmap(
            x="columns",
            y="index",
            cmap="viridis",
            width=800,
            height=800,
            colorbar=True,
            title="Coalescence rates",
        )
        return pn.pane.HoloViews(hm, sizing_mode="stretch_width")

    def sidebar(self):
        return pn.Card(
            self.param.num_time_bins,
            self.param.window_size,
            collapsed=False,
            title="Coalescence rates plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )


class CoalescenceRatesPage(View):
    key = "coalescence_rates"
    title = "Coalescence Rates"
    data = param.ClassSelector(class_=CoalescenceHeatmap)

    def __init__(self, **params):
        super().__init__(**params)
        self.data = CoalescenceHeatmap(datastore=self.datastore)

    def __panel__(self):
        return pn.Column(
            pn.pane.Markdown("## Coalescence Rates Mockup"),
            self.data,
        )

    def sidebar(self):
        return pn.Column(
            self.data.sidebar,
        )
