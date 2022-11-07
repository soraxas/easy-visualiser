import zipfile
from typing import Tuple

import numpy as np
from scipy.interpolate import griddata
from vispy import scene

from plannerGraphVisualiser import KeepoutZone
from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)
from .easy_visualiser.plugin_capability import (
    FileModificationGuardableMixin,
    IntervalUpdatableMixin,
)
from plannerGraphVisualiser.visualisable_bathymetry import VisualisableBathy

AVG_OCEAN_DEPTH = 4_000


def create_grid_mesh(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    z_vals: np.ndarray,
    nums: Tuple[float, float],
    x_bound: Tuple[float, float] = None,
    y_bound: Tuple[float, float] = None,
):
    if x_bound is None:
        x_bound = x_vals.min(), x_vals.max()
    if y_bound is None:
        y_bound = y_vals.min(), y_vals.max()
    # Define a regular grid over the data
    xr = np.linspace(x_bound[0], x_bound[1], nums[0])
    yr = np.linspace(y_bound[0], y_bound[1], nums[1])
    xr, yr = np.meshgrid(xr, yr)

    # evaluate the z-values at the regular grid through cubic interpolation
    Z = griddata(
        (x_vals, y_vals),
        z_vals,
        (xr, yr),
        method="nearest",
        # method="cubic",
        # method="linear",
    )
    return xr[0, :], yr[:, 0], Z


class VisualisableKOZ(
    FileModificationGuardableMixin, IntervalUpdatableMixin, VisualisablePlugin
):
    keepout_zone_mesh = None

    def __init__(
        self,
        graph_data_path: str,
    ):
        super().__init__()
        self.data_path = graph_data_path

    @property
    def name(self):
        return "koz"

    @property
    def target_file(self) -> str:
        return self.data_path

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.keepout_zone_mesh = scene.Mesh(
            # vertices=[],
            # faces=[],
            parent=self.visualiser.view.scene,
            # color=(.5, .5, .5),
            color=(0.5, 0.5, 0.5, 0.7),
        )
        self.keepout_zone_mesh.set_gl_state("translucent")

    def on_update(self):

        vertices = []
        faces = []

        try:
            keepout_zones = self.__get_keepout_zones(
                self.other_plugins.bathymetry.bathy_interp
            )

        except zipfile.BadZipFile as e:
            print(e)
            keepout_zones = []

        for keepout_zone in keepout_zones:
            # start new index for faces according to current vertices list length
            _faces = np.array(list(keepout_zone.faces)) + len(vertices)

            vertices.extend(list(keepout_zone.vertices))
            faces.extend(_faces)
        if len(keepout_zones) > 0:
            vertices = np.array(vertices)
            _faces = np.array(_faces)
            self.other_plugins.zscaler.scaler(vertices)

            self.keepout_zone_mesh.set_data(
                vertices=vertices,
                faces=np.array(faces),
            )

    def __get_keepout_zones(self, bathy_interp):
        pdata = np.load(self.target_file)

        return [
            KeepoutZone(
                depth=self.other_plugins.zscaler.scaler(
                    pdata["keepout_zones_depths"][i]
                ),
                points=pdata[f"keepout_zones_{i}"],
                bathy_interp=bathy_interp,
            )
            for i in range(len(pdata["keepout_zones_depths"]))
        ]
