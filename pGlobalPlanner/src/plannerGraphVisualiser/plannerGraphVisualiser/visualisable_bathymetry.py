from typing import Tuple, Dict

import numpy as np
from scipy.interpolate import griddata, NearestNDInterpolator
from vispy.color import get_colormap

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
    IntervalUpdatableMixin,
)
from .easy_visualiser.plugin_capability import (
    ToggleableMixin,
    CallableAndFileModificationGuardableMixin,
)
from plannerGraphVisualiser.easy_visualiser.dummy import DUMMY_AXIS_VAL
from plannerGraphVisualiser.easy_visualiser.visuals.gridmesh import FixedGridMesh
from plannerGraphVisualiser.easy_visualiser.modal_control import ModalControl
from .easy_visualiser.utils import ToggleableBool


def create_grid_mesh(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    z_vals: np.ndarray,
    nums: Tuple[float, float],
    x_bound: Tuple[float, float] = None,
    y_bound: Tuple[float, float] = None,
    method="nearest",
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
        method=method,
        # method="cubic",
        # method="linear",
    )
    return xr[0, :], yr[:, 0], Z


class VisualisableBathy(
    CallableAndFileModificationGuardableMixin,
    ToggleableMixin,
    IntervalUpdatableMixin,
    VisualisablePlugin,
):
    bathy_mesh = None
    bathy_interp: NearestNDInterpolator = None
    last_min_max_pos = None

    def __init__(
        self,
        bathy_toggle: ToggleableBool,
        bathy_colorscale_toggle: ToggleableBool,
        depth_datapath: str,
    ):
        super().__init__()
        self.bathy_toggle = bathy_toggle
        self.bathy_colorscale_toggle = bathy_colorscale_toggle
        self.depth_datapath = depth_datapath
        self.guarding_callable = lambda: self.bathy_toggle
        self.keys = [
            ModalControl(
                "b",
                [
                    ("b", "toggle bathymetry", self.__toggle_bathy_cb),
                    (
                        "s",
                        "toggle bathymetry deph colour scale",
                        self.__toggle_bathy_colour_scale_cb,
                    ),
                ],
                modal_name="bathymetry",
            )
        ]

    def __toggle_bathy_cb(self):
        self.bathy_toggle.toggle()
        self.toggle()

    def __toggle_bathy_colour_scale_cb(self):
        self.bathy_colorscale_toggle.toggle()
        self._last_modify_time = None
        self.update()

    @property
    def name(self):
        return "bathymetry"

    @property
    def target_file(self) -> str:
        return self.depth_datapath

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
            parent=self.visualiser.view.scene,
        )

    def __get_data(self) -> Dict:
        bathymetry = np.load(self.target_file)

        ###########################################
        # cache interp
        self.bathy_interp = NearestNDInterpolator(
            list(zip(bathymetry[:, 0], bathymetry[:, 1])),
            self.other_plugins.zscaler.scaler(bathymetry[:, 2]),
        )
        ###########################################

        grid_size = max(100, int(bathymetry[:, 0].shape[0] ** 0.5) - 30)
        xx, yy, zz = create_grid_mesh(
            bathymetry[:, 0], bathymetry[:, 1], bathymetry[:, 2], (grid_size, grid_size)
        )

        xx, yy = np.meshgrid(xx, yy, indexing="xy")

        zz = self.other_plugins.zscaler.scaler(zz)

        self.last_min_max_pos = np.empty((2, 3), dtype=np.float)
        self.last_min_max_pos[0, :] = bathymetry.min(0)  # cache
        self.last_min_max_pos[0, 2] = zz.min()
        self.last_min_max_pos[1, :] = bathymetry.max(0)  # cache
        self.last_min_max_pos[1, 2] = zz.max()

        data = dict(
            xs=xx,
            ys=yy,
            zs=zz,
        )
        if self.bathy_colorscale_toggle:
            cmap = get_colormap("jet")
            colours = cmap.map((zz - zz.min()) / (zz.max() - zz.min()))
            data["colors"] = colours.reshape(grid_size, grid_size, 4)
        return data

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        self.bathy_mesh.set_data(**self.__get_data())
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        if not self.bathy_colorscale_toggle:
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors = None
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors_indexed_by_faces = (
                None
            )
        self.bathy_mesh.set_data(
            xs=DUMMY_AXIS_VAL,
            ys=DUMMY_AXIS_VAL,
            zs=DUMMY_AXIS_VAL,
        )
        return True

    def on_update(self):
        self.turn_on_plugin()

        if not self.bathy_colorscale_toggle:
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors = None
            self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors_indexed_by_faces = (
                None
            )
        if not self.had_set_range:
            self.set_range()
