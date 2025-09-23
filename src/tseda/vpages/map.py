"""Module for creating a map of the world with sample locations.

Generate a hvplot map of the world with sample locations based on a
GeoPandas representation of the individuals data. The map is
interactive and can be drawn using different XYZ tiles.

TODO:

- Add linked brushing between the map and other panel objects /
  widgets
- Fix issue where map is rendered small and repeated tiles
"""

import geopandas
import hvplot.pandas  # noqa
import pandas as pd
import panel as pn
import param
import xyzservices.providers as xyz

from tseda import config
from tseda.datastore import IndividualsTable

from .core import View

tiles_options = {
    "WorldImagery": xyz.Esri.WorldImagery,
    "WorldTopoMap": xyz.Esri.WorldTopoMap,
    "WorldStreetMap": xyz.Esri.WorldStreetMap,
    "WorldTerrain": xyz.Esri.WorldTerrain,
    "WorldShadedRelief": xyz.Esri.WorldShadedRelief,
    "WorldPhysical": xyz.Esri.WorldPhysical,
    "WorldGrayCanvas": xyz.Esri.WorldGrayCanvas,
}


class GeoMap(View):
    """Make the Geomap plot. This class creates a hvplot that displays the map
    where the different samples were collected.

    Attributes:
        tiles_selector (pn.Selector): the selected tiles for the map
        vizualisation.
        tiles (str): the selected tile for the map.
        individuals_table (IndividualsTable): An instance of the
        IndividualsTable class, containing the information from the individuals
        table.

    Methods:
        __panel__() -> gdf.hvplot: Returns the Geomap as an Hvplot.
        sidebar() -> pn.Card: Defines the layout of the sidebar options for
        the Geomap.
    """

    individuals_table = param.ClassSelector(class_=IndividualsTable)

    tiles_selector = param.Selector(
        default="WorldPhysical",
        objects=list(tiles_options.keys()),
        doc="Select XYZ tiles for map",
    )
    tiles = tiles_options[tiles_selector.default]

    def __init__(self, **params):
        super().__init__(**params)
        self.individuals_table = self.datastore.individuals_table

    @pn.depends("individuals_table.refresh_button.value")
    def __panel__(self):
        """Returns the main content for the Geomap plot which is retrieved from
        the `datastore.tsm.ts` attribute.

        Returns:
            gdf.hvplot: the geomap plot as a Hvplot.
        """
        self.tiles = tiles_options[self.tiles_selector]
        df = self.datastore.individuals_table.data.rx.value
        df = df.loc[df.selected]
        color = self.datastore.color
        gdf = geopandas.GeoDataFrame(
            df.drop(["longitude", "latitude"], axis=1),
            geometry=geopandas.points_from_xy(df.longitude, df.latitude),
        )
        gdf["color"] = color.loc[~gdf.geometry.is_empty.values]
        gdf = gdf[gdf.geometry.is_valid]

        kw = {
            "geo": True,
            "tiles": self.tiles,
            "tiles_opts": {"alpha": 0.5},
            "responsive": True,
            "min_height": 600,
            "max_height": 600,
            "min_width": 600,
            "max_width": 600,
            "xlim": (-180, 180),
            "ylim": (-60, 70),
            "tools": ["wheel_zoom", "box_select", "tap", "pan", "reset"],
        }

        if gdf.empty:
            gdf = geopandas.GeoDataFrame(
                pd.DataFrame(index=[0]),
                geometry=geopandas.points_from_xy([0.0], [0.0]),
            )
            return gdf.hvplot(
                **kw,
                hover_cols=None,
                size=100,
                color=None,
                fill_alpha=0.0,
                line_color=None,
            )
        return gdf.hvplot(
            **kw,
            hover_cols=["name", "population", "sample_set_id"],
            size=100,
            color="color",
            fill_alpha=0.5,
            line_color="black",
        )

    def sidebar(self):
        """Returns the content of the sidbar options for the Geomap plot.

        Returns:
            pn.Card: The layout for the sidebar content area connected to the
            Geomap plot.
        """
        return pn.Card(
            self.param.tiles_selector,
            collapsed=True,
            title="Map options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )
