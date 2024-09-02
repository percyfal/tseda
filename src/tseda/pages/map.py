import hvplot.pandas  # noqa
import xyzservices.providers as xyz
import panel as pn
import param

pn.extension("hvplot")

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
    tiles_selector = param.Selector(
        default="WorldPhysical",
        objects=list(tiles_options.keys()),
        doc="Select XYZ tiles for map",
    )
    tiles = tiles_options[tiles_selector.default]

    def __init__(self, tsm, **kwargs):
        super().__init__(**kwargs)
        self.tsm = tsm
        self.gdf, self.colormap = self.setup_geomap_data()

    @param.depends("tiles_selector")
    def plot(self):
        self.tiles = tiles_options[self.tiles_selector]
        return self.world_map()

    # TODO: Add functionality to update the colormap
    def update_colormap(self):
        pass

    def setup_geomap_data(self):
        gdf = self.tsm.get_individuals(astype="gdf")[
            ["sample_set_id", "population", "geometry"]
        ]
        gdf = gdf.reset_index().set_index(
            ["id", "sample_set_id", "population"]
        )
        colormap = self.tsm.colormap()[~gdf.geometry.is_empty]
        gdf = gdf[~gdf.geometry.is_empty]
        return gdf, colormap

    def world_map(self):
        """Make world map plot"""
        return self.gdf.hvplot.points(
            hover_cols=["id", "population", "sample_set_id"],
            geo=True,
            tiles=self.tiles,
            tiles_opts={"alpha": 0.5},
            width=1400,
            height=800,
            size=100,
            color=self.colormap,
            tools=["wheel_zoom", "box_select", "tap", "pan", "reset"],
            fill_alpha=0.5,
            line_color="black",
        )
