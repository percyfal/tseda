"""Core vpages module.

Provides View helper class for panel plots and helper functions common to
pages.
"""

import numpy as np
import panel as pn
import param
from panel.viewable import Viewer

from tseda.datastore import DataStore


class View(Viewer):
    key = param.String()
    title = param.String()

    def __init__(self, *, datastore: DataStore, **params):
        super().__init__(**params)
        self.datastore = datastore

    def sidebar(self):
        return pn.Column(pn.pane.Markdown(f"# {self.title}"))


def make_windows(window_size, sequence_length):
    """Make windows for statistics."""
    num_windows = int(sequence_length / window_size)
    windows = np.linspace(0, sequence_length, num_windows + 1)
    windows[-1] = sequence_length
    return windows


# NB: currently unused
def make_sample_sets(inds):
    sample_sets = {}
    samples = []
    for _, ind in inds.iterrows():
        sample_set = ind.sample_set_id
        if sample_set not in sample_sets:
            sample_sets[sample_set] = []
        sample_sets[sample_set].append(ind.id)
        samples.append(ind.id)
    return sample_sets
