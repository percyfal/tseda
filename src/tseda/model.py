"""Tseda data model module.

Class definitions for data models underlying all data views in tseda.
The main data model is the tsbrowse.TSModel class which wraps a
tskit.TreeSequence loaded from a .tszip file. This model is treated as
immutable by the main application. Tseda adds two helper dataclasses to
deal with individuals and sample sets, Indivudals and SampleSets.
Instances of these classes are editable and can be used to filter the
data for visualization, e.g. by selecting individuals or sample sets,
or customization of sample set colors.

TODO:

- simplify haplotype_gnn function
- cache computations!

"""

import dataclasses
import json
import re
from enum import Enum

import daiquiri
import numpy as np
import tskit
from bokeh.palettes import Set3

from tseda import config

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
        try:
            ret = json.loads(obj.metadata.decode())
        except json.JSONDecodeError:
            ret = None
        return ret
    return obj.metadata


def parse_metadata(obj, regex):
    """Retrieve metadata value pairs based on key regex"""
    md = decode_metadata(obj)
    if md is None:
        return
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
    predefined: bool = False

    colormap = config.COLORS

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
    population_name: str = None
    sample_set_id: np.int32 = None
    sample_set_name: str = None
    sample_set_color: str = None
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
