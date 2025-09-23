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
import pathlib
import re
from enum import Enum

import daiquiri
import numpy as np
import pandas as pd
import tskit
import tszip
import zarr
from bokeh.palettes import Set3

from tseda import config

from . import TSEDA_DATA_VERSION

logger = daiquiri.getLogger("tseda")


class DataTypes(Enum):
    """Enum for getter method data types."""

    LIST = "list"
    DATAFRAME = "df"
    GEO_DATAFRAME = "gdf"


def decode_metadata(obj):
    """Decode metadata from bytes to dict."""
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
    """Retrieve metadata value pairs based on key regex."""
    md = decode_metadata(obj)
    if md is None:
        return
    key = list(filter(lambda x: regex.match(x), md.keys()))
    if len(key) >= 1:
        return md.get(key[0])
    return None


def palette(cmap=Set3[12], n=12, start=0, end=1):
    """Make a small colorblind-friendly palette."""
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
    """A class to contain sample sets."""

    name_re = re.compile(r"^(name|Name|population|Population)$")

    sample_set_id: np.int32
    name: str = None
    color: str = None
    population: dataclasses.InitVar[tskit.Population | None] = None
    predefined: bool = False

    colormap = config.COLORS

    def __post_init__(self, population):
        if self.color is None:
            self.color = self.colormap[self.sample_set_id % len(self.colormap)]
        if population is not None:
            self.name = parse_metadata(population, self.name_re)
        if self.name is None:
            self.name = f"SampleSet-{self.sample_set_id}"


@dataclasses.dataclass
class Individual(tskit.Individual):
    """A class to handle individuals."""

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
        """Return samples (nodes) associated with individual."""
        return self.nodes

    def toggle(self) -> None:
        """Toggle selection status."""
        self.selected = not self.selected

    def select(self) -> None:
        """Select individual."""
        self.selected = True

    def deselect(self) -> None:
        """Deselect individual."""
        self.selected = False


class TSModel:
    """
    A class to handle a tskit TreeSequence and associated data.
    """

    def __init__(self, tseda_path):
        tseda_path = pathlib.Path(tseda_path)
        root = zarr.open(zarr.ZipStore(tseda_path, mode="r"))
        if (
            "tseda" not in root.attrs
            or "data_version" not in root.attrs["tseda"]
        ):
            raise ValueError("File is not a tseda file, run tseda preprocess")
        if root.attrs["tseda"]["data_version"] != TSEDA_DATA_VERSION:
            raise ValueError(
                f"File {tseda_path} has version "
                f"{root.attrs['tseda']['data_version']}, "
                f"but this version of tseda expects version "
                f"{TSEDA_DATA_VERSION} rerun tseda preprocess"
            )
        self.ts = tszip.load(tseda_path)
        self.name = tseda_path.stem
        self.full_path = tseda_path
        ts_tables = self.ts.tables
        for table_name in [
            "edges",
            "mutations",
            "nodes",
            "sites",
            "individuals",
            "populations",
            "migrations",
            "provenances",
        ]:
            ts_table = getattr(ts_tables, table_name)
            # filter out ragged arrays with offset
            array_names = set(root[table_name].keys())
            ragged_array_names = {
                "_".join(name.split("_")[:-1])
                for name in array_names
                if "offset" in name
            }
            array_names -= {"metadata_schema"}
            array_names -= {f"{name}_offset" for name in ragged_array_names}
            arrays = {}
            for name in array_names:
                if hasattr(ts_table, name):
                    if name == "metadata":
                        packed_metadata = ts_table.metadata.tobytes()
                        offset = ts_table.metadata_offset
                        arrays[name] = [
                            str(
                                ts_table.metadata_schema.decode_row(
                                    packed_metadata[start:end]
                                )
                            )
                            for start, end in zip(offset[:-1], offset[1:])
                        ]
                    # It would be nice to just let tskit do this
                    # decoding, but that takes a long time especially
                    # for sites which objectify their mutations as you
                    # iterate.
                    elif (
                        name in ragged_array_names
                        and table_name != "provenances"
                    ):
                        packed_data = getattr(ts_table, name)
                        if name not in ["location", "parents"]:
                            packed_data = packed_data.tobytes()
                        offset = getattr(ts_table, f"{name}_offset")
                        arrays[name] = [
                            packed_data[start:end]
                            for start, end in zip(offset[:-1], offset[1:])
                        ]
                        if name not in ["location", "parents"]:
                            arrays[name] = [
                                row.decode() for row in arrays[name]
                            ]
                    elif name in ragged_array_names:
                        arrays[name] = [
                            getattr(row, name)
                            for row in getattr(self.ts, table_name)()
                        ]
                    else:
                        arrays[name] = getattr(ts_table, name)
                else:
                    arrays[name] = root[table_name][name][:]
            df = pd.DataFrame(arrays)
            df["id"] = df.index
            setattr(self, f"{table_name}_df", df)

        for table_name in ["trees"]:
            arrays = {
                name: root[table_name][name][:]
                for name in root[table_name].keys()
            }
            df = pd.DataFrame(arrays)
            df["id"] = df.index
            setattr(self, f"{table_name}_df", df)

        @property
        def file_uuid(self):
            return self.ts.file_uuid
