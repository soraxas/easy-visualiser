from typing import Dict, Tuple

import numpy as np
from scipy.interpolate import NearestNDInterpolator, griddata
from scipy.spatial import cKDTree
from vispy.color import get_colormap

from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import (
    CallableAndFileModificationGuardableMixin,
    IntervalUpdatableMixin,
    ToggleableMixin,
)
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import ToggleableBool
from easy_visualiser.utils.dummy import DUMMY_AXIS_VAL
from easy_visualiser.visuals.gridmesh import FixedGridMesh


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


def estimate_grid_resolution(kd_tree, bathy_points: np.ndarray) -> float:
    dist, ii = kd_tree.query(bathy_points, k=2)

    # we would use the second-closest point to estimate the resolution of bluelink grid
    second_closest = dist[:, 1]
    return np.mean(second_closest[second_closest > 0])


class VisualisableBathy(
    CallableAndFileModificationGuardableMixin,
    ToggleableMixin,
    IntervalUpdatableMixin,
    VisualisablePlugin,
):
    bathy_mesh = None
    bathy_interp: NearestNDInterpolator = None
    last_min_max_pos = None
    seabed_colour = (0.78, 0.78, 0.78, 1)
    land_colour = (0.522, 0.341, 0.137, 1)

    def __init__(
        self,
        bathy_toggle: ToggleableBool,
        bathy_colorscale_toggle: ToggleableBool,
        depth_datapath: str,
        only_display_actual_bathy: bool = True,
    ):
        super().__init__()
        self.bathy_toggle = bathy_toggle
        self.bathy_colorscale_toggle = bathy_colorscale_toggle
        self.depth_datapath = depth_datapath
        self._only_display_actual_bathy = only_display_actual_bathy
        self.guarding_callable = lambda: self.bathy_toggle
        self.add_mapping(
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
        )

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
            parent=self.visualiser.visual_parent,
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

        if self._only_display_actual_bathy:
            given_bathy_points = np.stack([bathymetry[:, 0], bathymetry[:, 1]]).T
            tree = cKDTree(given_bathy_points)

            dist, ii = tree.query(np.stack([xx.ravel(), yy.ravel()]).T)

            # match our shape with our bathy mesh grid
            dist = dist.reshape(xx.shape)

            resolution = estimate_grid_resolution(tree, given_bathy_points)

            mask = (
                dist > (np.sqrt(2) * resolution)
            ) & (  # far away from existing bathy point
                zz <= 0
            )  # and it's not above ground

            xx[mask] = np.nan
            yy[mask] = np.nan

        zz = self.other_plugins.zscaler.scaler(zz)

        is_land_mask = zz >= 0

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
        else:
            data["colors"] = np.empty((grid_size, grid_size, 4), dtype=np.float)
            data["colors"][~is_land_mask] = self.seabed_colour
            data["colors"][is_land_mask] = self.land_colour

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

        # if not self.bathy_colorscale_toggle:
        #     self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors = None
        #     self.bathy_mesh._GridMeshVisual__meshdata._vertex_colors_indexed_by_faces = (
        #         None
        #     )
        if not self.had_set_range:
            self.set_range()
