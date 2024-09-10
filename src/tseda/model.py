import dataclasses
import json
import re
from enum import Enum

import daiquiri
import geopandas
import numpy as np
import pandas as pd
import tskit
from bokeh.palettes import Set3
from tsbrowse.model import TSModel

logger = daiquiri.getLogger("tseda")


class DataTypes(Enum):
    """
    Enum for getter method data types
    """

    LIST = "list"
    DATAFRAME = "df"
    GEO_DATAFRAME = "gdf"


def decode_metadata(obj):
    """Decode metadata from bytes to dict"""
    if not hasattr(obj, "metadata"):
        return None
    if isinstance(obj.metadata, bytes):
        return json.loads(obj.metadata.decode())
    return obj.metadata


def parse_metadata(obj, regex):
    """Retrieve metadata value pairs based on key regex"""
    md = decode_metadata(obj)
    key = list(filter(lambda x: regex.match(x), md.keys()))
    if len(key) >= 1:
        return md.get(key[0])
    return None


def palette(cmap=Set3[12], n=12, start=0, end=1):
    """Make a small colorblind-friendly palette"""
    import matplotlib

    linspace = np.linspace(start, end, n)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "customcmap", cmap
    )
    palette = cmap(linspace)
    hex_palette = [matplotlib.colors.rgb2hex(c) for c in palette]
    return hex_palette


@dataclasses.dataclass
class SampleSet:
    """
    A class to contain sample sets.
    """

    name_re = re.compile(r"^(name|Name|population|Population)$")

    id: np.int32
    name: str = None
    color: str = None
    population: dataclasses.InitVar[tskit.Population | None] = None

    colormap = palette()

    def __post_init__(self, population):
        if self.color is None:
            self.color = self.colormap[self.id % len(self.colormap)]
        if population is not None:
            self.name = parse_metadata(population, self.name_re)
        if self.name is None:
            self.name = f"SampleSet-{self.id}"


@dataclasses.dataclass
class Individual(tskit.Individual):
    """
    A class to handle individuals.
    """

    name_re = re.compile(r"^(name|Name|SM)$")
    longitude_re = re.compile(r"^(longitude|Longitude|lng|long)$")
    latitude_re = re.compile(r"^(latitude|Latitude|lat)$")

    population: np.int32 = None
    longitude: np.float64 = None
    latitude: np.float64 = None
    name: str = None
    sample_set_id: np.int32 = None
    selected: bool = True

    def __init__(self, individual: tskit.Individual):
        super().__init__(
            id=individual.id,
            flags=individual.flags,
            location=individual.location,
            metadata=individual.metadata,
            nodes=individual.nodes,
            parents=individual.parents,
        )
        self.population = individual.population
        self.sample_set_id = self.population
        self.__post_init__()

    def __post_init__(self) -> None:
        self.longitude = parse_metadata(self, self.longitude_re)
        self.latitude = parse_metadata(self, self.latitude_re)
        self.name = parse_metadata(self, self.name_re)

    @property
    def samples(self):
        """Return samples (nodes) associated with individual"""
        return self.nodes

    def toggle(self) -> None:
        """Toggle selection status"""
        self.selected = not self.selected

    def select(self) -> None:
        """Select individual"""
        self.selected = True

    def deselect(self) -> None:
        """Deselect individual"""
        self.selected = False


@dataclasses.dataclass
class Sample(tskit.Node):
    """A class to handle samples."""

    sample_set_id: np.int32 = None
    selected: bool = True

    def __init__(self, node: tskit.Node):
        super().__init__(
            id=node.id,
            flags=node.flags,
            time=node.time,
            population=node.population,
            individual=node.individual,
            metadata=node.metadata,
        )
        self.__post_init__()

    def __post_init__(self) -> None:
        self.sample_set_id = self.population

    def toggle(self) -> None:
        """Toggle selection status"""
        self.selected = not self.selected

    def select(self) -> None:
        """Select sample"""
        self.selected = True

    def deselect(self) -> None:
        """Deselect sample"""
        self.selected = False


# TODO: add relevant methods to caching. Cache id should be calculated
# with respect to the selected sample sets
class TSEdaModel(TSModel):
    """Tree sequence eda model"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sample_sets = [
            SampleSet(id=pop.id, population=pop)
            for pop in self.ts.populations()
        ]
        self.individuals = self._init_individuals()
        self.samples = self._init_samples()

    def _init_individuals(self):
        result = []
        for ts_ind in self.ts.individuals():
            ind = Individual(individual=ts_ind)
            result.append(ind)
        return result

    def _init_samples(self):
        result = []
        for ts_ind in self.ts.individuals():
            for node in ts_ind.nodes:
                sample = Sample(self.ts.node(node))
                result.append(sample)
        return result

    def _get_data(self, attr="individuals", astype="list", deselected=True):
        """Generic function to get data from individuals or samples.

        Individuals and samples are stored as lists of objects. This
        function returns a list, DataFrame or GeoDataFrame of
        individuals / samples.

        Parameters

        attr: str
            The attribute to get data from. Can be "individuals" or
            "samples".
        astype: str
            The type of data to return. Can be "list", "df" or "gdf".
        deselected: bool
            If True, return all individuals / samples. If False, return
            only selected individuals / samples.

        Returns

        data: list / DataFrame / GeoDataFrame
            The data requested.
        """
        if deselected:
            data = self.__getattribute__(attr)
        else:
            data = [d for d in self.__getattribute__(attr) if d.selected]
        if astype == "list":
            return data
        if astype == DataTypes.DATAFRAME.value:
            df = pd.DataFrame(data)
            return df
        elif astype == DataTypes.GEO_DATAFRAME.value:
            df = pd.DataFrame(data)
            return geopandas.GeoDataFrame(
                df.drop(["longitude", "latitude"], axis=1),
                geometry=geopandas.points_from_xy(df.longitude, df.latitude),
            )

    def get_individuals(self, astype="list", deselected=True):
        """Return a list / DataFrame / GeoDataFrame of individuals.

        Parameters

        astype: str
            The type of data to return. Can be "list", "df" or "gdf".
        deselected: bool
            If True, return all individuals. If False, return only

        Returns

        data: list / DataFrame / GeoDataFrame
            The data requested.
        """
        data = self._get_data("individuals", astype, deselected)
        if isinstance(data, list):
            return data
        return data.set_index(["id"])

    def get_samples(self, astype="list", deselected=True):
        """
        Return a list / DataFrame of samples.

        Parameters

        astype: str
            The type of data to return. Can be "list" or "df".
        deselected: bool
            If True, return all samples. If False, return only selected
            samples.

        Returns

            data: list / DataFrame
                The data requested.

        """
        if astype == DataTypes.GEO_DATAFRAME.value:
            raise ValueError("geo data frame not supported for samples")
        data = self._get_data("samples", astype, deselected)
        if isinstance(data, list):
            return data
        return data.set_index(["id"])

    def update_individual_sample_set(self, ind_id, sample_set_id):
        """Update the sample set of an individual and its samples."""
        self.individuals[ind_id].sample_set_id = sample_set_id
        for sid in self.individuals[ind_id].samples:
            self.samples[sid].sample_set_id = sample_set_id

    def toggle_individual(self, ind_id):
        """Toggle the selection status of an individual and its samples."""
        self.individuals[ind_id].toggle()
        for sid in self.individuals[ind_id].samples:
            self.samples[sid].toggle()

    def deselect_individual(self, ind_id):
        """Deselect an individual and its samples"""
        self.individuals[ind_id].deselect()
        for sid in self.individuals[ind_id].samples:
            self.samples[sid].deselect()

    def select_individual(self, ind_id):
        """Select an individual and its samples"""
        self.individuals[ind_id].select()
        for sid in self.individuals[ind_id].samples:
            self.samples[sid].select()

    def update_individual(self, index, prop, value):
        """Update individual property. Wrapper for updating individual
        on property 'selected' or 'sample_set_id'
        """
        if prop == "selected":
            self.toggle_individual(index)
        elif prop == "sample_set_id":
            print(f"Setting {index} to {value}")
            self.update_individual_sample_set(index, value)

    def create_sample_set(self, name):
        """Create a new sample set.

        Add a new sample set where the sample id is the sequential
        number following the last sample set id.
        """
        newid = len(self.sample_sets)
        ss = SampleSet(id=np.int32(newid), name=name)
        self.sample_sets.append(ss)
        return newid

    def make_sample_sets(self):
        """Wrapper to make current sample sets from selected individuals"""
        sample_sets = {}
        samples = []
        for sample in self.samples:
            if not sample.selected:
                continue
            samples.append(sample.id)
            if sample.sample_set_id not in sample_sets:
                sample_sets[sample.sample_set_id] = []
            sample_sets[sample.sample_set_id].append(sample.id)
        return samples, sample_sets

    def update_sample_set(self, index, prop, value):
        """Update sample set property 'color' or 'name'"""
        if prop == "color":
            self.sample_sets[index].color = value
        elif prop == "name":
            self.sample_sets[index].name = value

    def get_sample_sets(self, indexes=None):
        """Return sample sets"""
        samples, sample_sets = self.make_sample_sets()
        if indexes:
            return [sample_sets[i] for i in indexes]
        return [sample_sets[i] for i in sample_sets]

    def get_sample_set(self, index):
        """Return single sample set"""
        samples, sample_sets = self.make_sample_sets()
        return sample_sets[index]

    def get_sample_set_by_name(self, name):
        """Return single sample set by name"""
        for sample_set in self.sample_sets:
            if sample_set.name == name:
                return sample_set

    # TODO: make cached_property, taking into account selected sample
    # sets
    def gnn(self):
        """
        Returns a GNN object for the tree sequence
        """
        samples, sample_sets = self.make_sample_sets()
        gnn = self.ts.genealogical_nearest_neighbours(
            samples, sample_sets=list(sample_sets.values())
        )
        df = pd.DataFrame(
            gnn,
            columns=[i for i in sample_sets],  # pyright: ignore
        )
        df["sample_set_id"] = [self.samples[i].sample_set_id for i in samples]
        df["id"] = [self.samples[i].individual for i in samples]
        df["sample_id"] = df.index
        df.set_index(["sample_set_id", "sample_id", "id"], inplace=True)
        return df

    def colormap(self, by_sample=False, deselected=True):
        """
        Get colormap for individuals or samples
        """
        result = []
        if by_sample:
            data = self.get_samples(deselected=deselected)
        else:
            data = self.get_individuals(deselected=deselected)
        for d in data:
            result.append(self.sample_sets[d.sample_set_id].color)
        return np.array(result)

    def sample_sets_view(self):
        """
        Returns a sample sets view of the current state
        """
        return pd.DataFrame(self.sample_sets).set_index(["id"])
