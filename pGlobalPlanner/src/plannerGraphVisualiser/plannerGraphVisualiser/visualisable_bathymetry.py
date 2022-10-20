import os
from typing import Tuple, Optional, Dict, Callable

import numpy as np
from scipy.interpolate import griddata, NearestNDInterpolator
from vispy.color import get_colormap

from plannerGraphVisualiser.abstract_visualisable_plugin import (
    VisualisablePlugin,
    ToggleableMixin,
    FileModificationGuardableMixin,
    UpdatableMixin,
)
from plannerGraphVisualiser.dummy import DUMMY_AXIS_VAL
from plannerGraphVisualiser.gridmesh import FixedGridMesh


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


class VisualisableBathy(
    FileModificationGuardableMixin, ToggleableMixin, UpdatableMixin, VisualisablePlugin
):
    bathy_mesh = None
    bathy_intert: NearestNDInterpolator = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keys = [
            ("b", "toggle bathymetry", self.__toggle_bathy_cb),
            (
                "s",
                "toggle bathymetry deph colour scale",
                self.__toggle_bathy_colour_scale_cb,
            ),
        ]

    def __toggle_bathy_cb(self):
        self.args.bathymetry = not self.args.bathymetry
        self.toggle()

    def __toggle_bathy_colour_scale_cb(self):
        self.args.bathymetry_colour_scale = not self.args.bathymetry_colour_scale
        self._last_modify_time = None
        self.update()

    @property
    def name(self):
        return "bathymetry"

    @property
    def target_file(self) -> str:
        return self.args.depth_datapath

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.bathy_mesh = FixedGridMesh(
            # **data,
            xs=DUMMY_AXIS_VAL,
            ys=DUMMY_AXIS_VAL,
            zs=DUMMY_AXIS_VAL,
            shading="smooth",
            # shading='flat',
            # shading=None,
            # color='blue',
            parent=self.args.view.scene,
        )

    def __get_data(self) -> Dict:
        bathymetry = np.load(self.target_file)

        ###########################################
        # cache interp
        self.bathy_interp = NearestNDInterpolator(
            list(zip(bathymetry[:, 0], bathymetry[:, 1])),
            self.args.z_scaler(bathymetry[:, 2]),
        )
        ###########################################

        grid_size = max(100, int(bathymetry[:, 0].shape[0] ** 0.5) - 30)
        xx, yy, zz = create_grid_mesh(
            bathymetry[:, 0], bathymetry[:, 1], bathymetry[:, 2], (grid_size, grid_size)
        )

        xx, yy = np.meshgrid(xx, yy, indexing="xy")

        zz = self.args.z_scaler(zz)

        data = dict(
            xs=xx,
            ys=yy,
            zs=zz,
        )
        if self.args.bathymetry_colour_scale:
            cmap = get_colormap("jet")
            colours = cmap.map((zz - zz.min()) / (zz.max() - zz.min()))
            data["colors"] = colours.reshape(grid_size, grid_size, 4)
        return data

    def turn_on_plugin(self):
        super().turn_on_plugin()
        self.bathy_mesh.set_data(**self.__get_data())

    def turn_off_plugin(self):
        super().turn_off_plugin()
        if not self.args.bathymetry_colour_scale:
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors = None
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors_indexed_by_faces = (
                None
            )
        self.bathy_mesh.set_data(
            xs=DUMMY_AXIS_VAL,
            ys=DUMMY_AXIS_VAL,
            zs=DUMMY_AXIS_VAL,
        )

    def on_update(self):
        self.turn_on_plugin()

        if not self.args.bathymetry_colour_scale:
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors = None
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors_indexed_by_faces = (
                None
            )

        return
        ####
