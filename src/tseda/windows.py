"""Windows-related classes and functions"""

import numpy as np


def make_windows(window_size, sequence_length):
    """Make windows for statistics."""
    num_windows = int(sequence_length / window_size)
    windows = np.linspace(0, sequence_length, num_windows + 1)
    windows[-1] = sequence_length
    return windows
