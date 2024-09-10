"""Helper code to compute genealogical nearest neighbours along
haplotypes.

Based on code from tskit.tests.test_stats:

https://github.com/tskit-dev/tskit/pull/683/files#diff-e5e589330499b325320b2e3c205eaf350660b50691d3e1655f8789683e49dca6R399

"""

import numpy as np
import tskit
from tqdm import tqdm


def parse_time_windows(ts, time_windows):
    if time_windows is None:
        time_windows = [0.0, ts.max_root_time]
    return np.array(time_windows)


def windowed_genealogical_nearest_neighbours(  # noqa: C901
    ts,
    focal,
    reference_sets,
    windows=None,
    time_windows=None,
    span_normalise=True,
    time_normalise=True,
):
    reference_set_map = np.full(ts.num_nodes, tskit.NULL, dtype=int)
    for k, reference_set in reference_sets.items():
        for u in reference_set:
            if reference_set_map[u] != tskit.NULL:
                raise ValueError("Duplicate value in reference sets")
            reference_set_map[u] = k

    windows_used = windows is not None
    time_windows_used = time_windows is not None
    windows = ts.parse_windows(windows)
    num_windows = windows.shape[0] - 1
    time_windows = parse_time_windows(ts, time_windows)
    num_time_windows = time_windows.shape[0] - 1
    A = np.zeros(
        (num_windows, num_time_windows, len(focal), len(reference_sets))
    )
    K = len(reference_sets)
    parent = np.full(ts.num_nodes, tskit.NULL, dtype=int)
    sample_count = np.zeros((ts.num_nodes, K), dtype=int)
    time = ts.tables.nodes.time
    norm = np.zeros((num_windows, num_time_windows, len(focal)))

    # Set the initial conditions.
    for k, v in reference_sets.items():
        print(k, v)
    print(list(reference_sets.keys()))
    for j in range(K):
        sample_count[reference_sets[j], j] = 1

    window_index = 0
    # Loop the tree sequence
    for (t_left, t_right), edges_out, edges_in in tqdm(ts.edge_diffs()):
        for edge in edges_out:
            parent[edge.child] = tskit.NULL
            v = edge.parent
            while v != tskit.NULL:
                sample_count[v] -= sample_count[edge.child]
                v = parent[v]
        for edge in edges_in:
            parent[edge.child] = edge.parent
            v = edge.parent
            while v != tskit.NULL:
                sample_count[v] += sample_count[edge.child]
                v = parent[v]

        # Update the windows
        assert window_index < num_windows
        while (
            windows[window_index] < t_right and window_index + 1 <= num_windows
        ):
            w_left = windows[window_index]
            w_right = windows[window_index + 1]
            left = max(t_left, w_left)
            right = min(t_right, w_right)
            span = right - left
            # Process this tree.
            for j, u in enumerate(focal):
                focal_reference_set = reference_set_map[u]
                delta = int(focal_reference_set != tskit.NULL)
                p = u
                while p != tskit.NULL:
                    total = np.sum(sample_count[p])
                    if total > delta:
                        break
                    p = parent[p]
                if p != tskit.NULL:
                    scale = span / (total - delta)
                    time_index = np.searchsorted(time_windows, time[p]) - 1
                    if 0 <= time_index < num_time_windows:
                        for k in range(len(reference_sets)):
                            n = sample_count[p, k] - int(
                                focal_reference_set == k
                            )
                            A[window_index, time_index, j, k] += n * scale
                        norm[window_index, time_index, j] += span
            assert span > 0
            if w_right <= t_right:
                window_index += 1
            else:
                # This interval crosses a tree boundary, so we update it again
                # in the next tree
                break

    # Reshape norm depending on normalization selected
    # Return NaN when normalisation value is 0
    if span_normalise and time_normalise:
        reshaped_norm = norm.reshape(
            (num_windows, num_time_windows, len(focal), 1)
        )
    elif span_normalise and not time_normalise:
        norm = np.sum(norm, axis=1)
        reshaped_norm = norm.reshape((num_windows, 1, len(focal), 1))
    elif time_normalise and not span_normalise:
        norm = np.sum(norm, axis=0)
        reshaped_norm = norm.reshape((1, num_time_windows, len(focal), 1))

    with np.errstate(invalid="ignore", divide="ignore"):
        A /= reshaped_norm
    A[np.all(A == 0, axis=3)] = np.nan

    # Remove dimension for windows and/or time_windows if parameter is None
    if not windows_used and time_windows_used:
        A = A.reshape((num_time_windows, len(focal), len(reference_sets)))
    elif not time_windows_used and windows_used:
        A = A.reshape((num_windows, len(focal), len(reference_sets)))
    elif not windows_used and not time_windows_used:
        A = A.reshape((len(focal), len(reference_sets)))
    return A
