"""Data transformation views.

Many widgets are based on data representations that are identical.
This module consists of mixin classes that transform the data into the
required format for the widgets.

"""

import itertools

import numpy as np
import pandas as pd
import param
import scipy

from tseda.logging import app_logger as logger

from .base import BaseView


class BaseMixin(BaseView):
    def __init__(self, **params):
        super().__init__(**params)
        self._data = None

    @property
    def data(self):
        if self._data is None:
            logger.error("No data has been set")
            raise Exception
        return self._data

    @data.setter
    def data(self, data):
        if not isinstance(data, pd.DataFrame):
            logger.error("View classes only support data frames")
            raise Exception
        self._data = data


class HierarchicalMixin(BaseMixin):
    zscore = param.Boolean(default=True, doc="Z-transform data")

    def __init__(self, **params):
        super().__init__(**params)
        self._row_linkage = None
        self._col_linkage = None

    def _calculate_linkage(
        self, axis=0, method="average", optimal_ordering=True, **kw
    ):
        if self._data is None:
            return
        data = self._data.copy()
        if axis == 1:
            data = data.T
        linkage = scipy.cluster.hierarchy.linkage(
            data, method=method, optimal_ordering=optimal_ordering, **kw
        )
        if axis == 0:
            self._row_linkage = linkage
        else:
            self._col_linkage = linkage
        return self

    def z_transform(self, axis=1):
        """Standardize mean and variance. 0=rows, 1=columns"""
        if axis == 1:
            zscore = self._data.copy()
        else:
            zscore = self._data.copy().T
        for col in list(zscore):
            zscore[col] = scipy.stats.zscore(zscore[col])
        if axis == 1:
            return zscore
        return zscore.T

    @property
    def data(self):
        if self.zscore:
            return self.z_transform()
        return self._data


class IndividualGNNMixin(HierarchicalMixin):
    def __init__(self, **params):
        super().__init__(**params)
        self._focal_population = None
        self._calculate_gnn()  # -> removes reactivity, never recalculated!

    # FIXME: this is no longer reactive!
    @param.depends("self.datastore.individuals_table.toggle_sample_set")
    def _calculate_gnn(self):
        # FIXME: simplify
        sample_sets = self.datastore.individuals_table.sample_sets()
        samples = [
            sample for sublist in sample_sets.values() for sample in sublist
        ]
        sstable = self.datastore.sample_sets_table.data.rx.value
        inds = self.datastore.individuals_table.data.rx.value
        samples2ind = [
            self.datastore.individuals_table.sample2ind[i] for i in samples
        ]

        ts = self.datastore.tsm.ts
        data = ts.genealogical_nearest_neighbours(
            samples, sample_sets=list(sample_sets.values())
        )
        self._data = pd.DataFrame(
            data,
            columns=[sstable.loc[i]["name"] for i in sample_sets],
        )
        self._focal_population = [
            sstable.loc[inds.loc[i].sample_set_id]["name"] for i in samples2ind
        ]

    @property
    def data(self):
        self._calculate_gnn()
        return super().data


class MeanGNNMixin(IndividualGNNMixin):
    def __init__(self, **params):
        super().__init__(**params)
        self._data["focal_population"] = self._focal_population
        self._data = self._data.groupby("focal_population").mean()

    @property
    def data(self):
        self._calculate_gnn()
        self._data["focal_population"] = self._focal_population
        self._data = self._data.groupby("focal_population").mean()
        if self.zscore:
            return self.z_transform()
        return self._data


class FstMixin(HierarchicalMixin):
    def __init__(self, **params):
        super().__init__(**params)
        self._calc_fst()

    def _calc_fst(self):
        sample_sets = self.datastore.individuals_table.sample_sets()
        if self.datastore.n_sample_sets_ids < self._min_sample_sets:
            return self.sample_select_warning
        sstable = self.datastore.sample_sets_table.data.rx.value
        ts = self.datastore.tsm.ts
        k = len(sample_sets)
        i = list(itertools.product(list(range(k)), list(range(k))))
        groups = [sstable.loc[i]["name"] for i in sample_sets]
        fst = ts.Fst(list(sample_sets.values()), indexes=i)
        self._data = pd.DataFrame(
            np.reshape(fst, shape=(k, k)), columns=groups, index=groups
        )

    @property
    def data(self):
        self._calc_fst()
        return super().data
