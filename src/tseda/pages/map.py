"""Module for creating a map of the world with sample locations

Generate a hvplot map of the world with sample locations based on a
GeoPandas representation of the individuals data. The map is
interactive and can be drawn using different XYZ tiles.

TODO:

- Add linked brushing between the map and other panel objects /
  widgets
- Add sizing_mode="stretch_width" to map

"""

import hvplot.pandas  # noqa
import xyzservices.providers as xyz
import param

tiles_options = {
    "WorldImagery": xyz.Esri.WorldImagery,
    "WorldTopoMap": xyz.Esri.WorldTopoMap,
    "WorldStreetMap": xyz.Esri.WorldStreetMap,
    "WorldTerrain": xyz.Esri.WorldTerrain,
    "WorldShadedRelief": xyz.Esri.WorldShadedRelief,
    "WorldPhysical": xyz.Esri.WorldPhysical,
    "WorldGrayCanvas": xyz.Esri.WorldGrayCanvas,
}


class GeoMap(param.Parameterized):
    height = param.Integer(default=400, doc="Height of the map")
    width = param.Integer(default=1200, doc="Width of the map")
    tiles_selector = param.Selector(
        default="WorldPhysical",
        objects=list(tiles_options.keys()),
        doc="Select XYZ tiles for map",
    )
    tiles = tiles_options[tiles_selector.default]

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.update_gdf()

    @param.depends("tiles_selector", "height", "width")
    def plot(self):
        self.tiles = tiles_options[self.tiles_selector]
        return self.world_map(self.height, self.width)

    def update_gdf(self):
        gdf = self.tsm.get_individuals(astype="gdf")[
            ["sample_set_id", "population", "geometry"]
        ]
        gdf = gdf.reset_index().set_index(
            ["id", "sample_set_id", "population"]
        )
        self._colormap = self.tsm.colormap()[~gdf.geometry.is_empty]
        self._gdf = gdf[~gdf.geometry.is_empty]

    @property
    def gdf(self):
        self.update_gdf()
        return self._gdf

    @property
    def colormap(self):
        self.update_gdf()
        return self._colormap

    def world_map(self, height, width):
        """Make world map plot using hvplot."""
        return self._gdf.hvplot.points(
            hover_cols=["id", "population", "sample_set_id"],
            geo=True,
            tiles=self.tiles,
            tiles_opts={"alpha": 0.5},
            width=width,
            height=height,
            size=100,
            color=self.colormap,
            tools=["wheel_zoom", "box_select", "tap", "pan", "reset"],
            fill_alpha=0.5,
            line_color="black",
        )
