#!/usr/bin/env python3
import dataclasses
import json
import os
import time
import traceback

import numpy as np
import plotly.express as px
import plotly.figure_factory as ff
import pymoos as moos
from plotly.subplots import make_subplots

OCEAN_CURRENT_VARIABLE = "OCEAN_CURRENT"
DEPTH_POINTS_VARIABLE = "DEPTH_POINTS_JSON"


@dataclasses.dataclass
class OceanCurrent:
    lat: float
    lon: float
    z: float
    u: float
    v: float

    @property
    def coor(self):
        return (round(self.lat, 0), round(self.lon, 0))

    def __hash__(self):
        return hash(self.coor)

    def __lt__(self, other):
        return self.coor < other.coor


class pGlobalPlannerMonitor(moos.comms):
    def __init__(self):
        super().__init__()
        self.connect_to_moos("localhost", 9000)

        self.depths = None
        self.currents = None

        self.use_real_map = True

    def connect_to_moos(self, moos_host, moos_port):
        self.set_on_connect_callback(self.__on_connect)
        self.set_on_mail_callback(self.__on_new_mail)
        self.run(moos_host, moos_port, self.__class__.__name__)
        if not self.wait_until_connected(2000):
            raise RuntimeError("Failed to connect to local MOOSDB")

    def __on_connect(self):
        try:
            self.register(OCEAN_CURRENT_VARIABLE, 0)
            self.register(DEPTH_POINTS_VARIABLE, 0)
        except Exception as e:
            return False
        return True

    def __on_new_mail(self):
        try:
            for msg in self.fetch():
                import pickle

                if msg.key() == OCEAN_CURRENT_VARIABLE:
                    self.currents = json.loads(msg.string())
                elif msg.key() == DEPTH_POINTS_VARIABLE:
                    self.depths = json.loads(msg.string())
            self.plot_all()
        except Exception as e:
            traceback.print_exc()
            return False
        return True

    def build_depth_trace(self, jsonobj):
        array_data = np.array(jsonobj)
        _lat = array_data[:, 1]
        _lon = array_data[:, 0]
        _z = array_data[:, 2]

        fig = px.scatter_mapbox(lat=_lat, lon=_lon, color=_z, zoom=3, height=300)
        if self.use_real_map:
            fig.update_layout(
                mapbox_style="white-bg",
                mapbox_layers=[
                    {
                        "below": "traces",
                        "sourcetype": "raster",
                        "sourceattribution": "United States Geological Survey",
                        "source": [
                            "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                        ],
                    }
                ],
            )
        else:
            fig.update_layout(
                mapbox_style="open-street-map",
            )
        fig.update_layout(
            #     mapbox_style="stamen-terrain",
            mapbox_zoom=6,
            mapbox_center_lat=_lat.mean(),
            mapbox_center_lon=_lon.mean(),
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
        )
        fig.data[0].marker.size = 5
        return fig

    def build_quiver(self, jsonobj):
        def get_quiver_data(jsonobj):
            currents = [
                OceanCurrent(
                    jsonobj["lat"][i],
                    jsonobj["lon"][i],
                    jsonobj["z"][i],
                    jsonobj["u"][i],
                    jsonobj["v"][i],
                )
                for i in range(len(jsonobj["v"]))
            ]
            currents = [c for c in currents if c.z > -50]

            _s = slice(None, None, 10)
            # _s = slice(0, 2)

            _lat = np.array([c.lat for c in currents[_s]])
            _lon = np.array([c.lon for c in currents[_s]])
            _u = np.array([c.u for c in currents[_s]])
            _v = np.array([c.v for c in currents[_s]])

            bo = _lat > -9.99

            _lat = _lat[bo]
            _lon = _lon[bo]
            _u = _u[bo]
            _v = _v[bo]

            fig_quiver = ff.create_quiver(
                _lon,
                _lat,
                _u,
                _v,
                scale=0.15,
                # arrow_scale=0.15,
                arrow_scale=0.35,
                name="quiver",
                line_color="red",
                line_width=0.25,
            )
            return fig_quiver.data[0]

        import pandas as pd

        # us_cities = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/us-cities-top-1k.csv")
        # us_cities = us_cities.query("State in ['New York', 'Ohio']")

        _data = get_quiver_data(jsonobj)

        fig = px.line_mapbox(lat=_data["y"], lon=_data["x"])

        fig.update_layout(
            #     mapbox_style="stamen-terrain",
            mapbox_zoom=7,
            mapbox_center_lat=np.array(jsonobj["lat"]).mean(),
            mapbox_center_lon=np.array(jsonobj["lon"]).mean(),
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
        )
        if self.use_real_map:
            fig.update_layout(
                mapbox_style="white-bg",
                mapbox_layers=[
                    {
                        "below": "traces",
                        "sourcetype": "raster",
                        "sourceattribution": "United States Geological Survey",
                        "source": [
                            "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                        ],
                    }
                ],
            )
        else:
            fig.update_layout(
                mapbox_style="open-street-map",
            )

        #     fig.show()
        fig.data[0].line.color = "red"
        return fig

    def plot_all(self):
        if any(map(lambda x: x is None, [self.currents, self.depths])):
            return

        fig = make_subplots(
            rows=2, cols=1, specs=[[dict(type="mapbox")], [dict(type="mapbox")]]
        )
        # fig.data = []

        _quiver_fig = self.build_quiver(self.currents)
        _depth_fig = self.build_depth_trace(self.depths)

        fig.add_trace(_quiver_fig.data[0], row=1, col=1)
        fig.add_trace(_depth_fig.data[0], row=2, col=1)

        fig.layout["mapbox"] = _quiver_fig.layout.mapbox
        fig.layout["mapbox"].domain.x = [0, 0.48]
        fig.layout["mapbox2"] = _depth_fig.layout.mapbox
        fig.layout["mapbox2"].domain.x = [0.52, 1]

        # fig.update_layout(height=600, width=800, title_text="Side By Side Subplots")
        # fig.show()
        fig.show()

    def spin(self):
        while True:
            time.sleep(1)


if __name__ == "__main__":
    moos_app = pGlobalPlannerMonitor()
    moos_app.spin()
