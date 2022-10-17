import zipfile

from vispy import app, scene, color
import numpy as np
import scipy
from vispy.visuals.colorbar import ColorBarVisual
from vispy.scene.visuals import XYZAxis, GridMesh, Text
from scipy.interpolate import griddata, NearestNDInterpolator
from ._impl import *
from typing import Tuple

DUMMY_LINE = np.array([[0, 0, 0], [0, 0.1, 0]])
DUMMY_CONNECT = np.array([[0, 1]])
DUMMY_COLOUR = np.array([[0, 0, 0], [0, 0, 0]])


class SolutionLine:
    def __init__(self, _scene, offset=None):
        self.path = None
        self.offset = offset
        self.line_visual = scene.Line(
            connect="strip",
            antialias=False,
            method="gl",
            # method='agg',
            parent=_scene,
            width=5,
            color="red",
        )

    def set_path(self, _path):
        if len(_path) <= 0:
            _path = DUMMY_LINE
        else:
            if self.offset:
                _path[:, -1] -= self.offset
        self.line_visual.set_data(pos=_path)


class GraphVisualiser:
    def __init__(self, args, cost_idx="all", offset=None):
        self.args = args
        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.args.view.scene, width=3
        )
        self.cost_idx = cost_idx

        self.offset = offset

        self.sol_lines = SolutionLine(self.args.view.scene)
        if self.args.extra_sol:
            self.fake_sol_lines = SolutionLine(self.args.view.scene, offset=200000)

        self.start_markers = None
        self.goal_markers = None
        self.axis_visual = None

        self.had_set_range = False
        self.avg_ocean_depth = 4_000

        self.z_scaler = Zscaler(z_scale_factor=self.args.z_scale_factor)

        self.bathy = None

        self.keepout_zone_mesh = scene.Mesh(
            # vertices=[],
            # faces=[],
            parent=self.args.view.scene,
            # color=(.5, .5, .5),
            color=(0.5, 0.5, 0.5, 0.7),
        )
        self.keepout_zone_mesh.set_gl_state("translucent")

        self.bathy_interp = None

    def update(self):
        self.update_bathymetry()
        self.update_graph()

    def update_bathymetry(self):
        if not os.path.exists(self.args.depth_datapath):
            return
        bathymetry = np.load(self.args.depth_datapath)

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
            )
            return xr[0, :], yr[:, 0], Z

        xx, yy, zz = create_grid_mesh(
            bathymetry[:, 0], bathymetry[:, 1], bathymetry[:, 2], (100, 100)
        )

        xx, yy = np.meshgrid(xx, yy, indexing="xy")

        zz = self.z_scaler.scale(zz)

        data = dict(
            xs=xx,
            ys=yy,
            zs=zz,
        )

        if self.bathy is None:
            self.bathy = GridMesh(
                **data,
                parent=self.args.view.scene,
            )
        else:
            self.bathy.set_data(**data)

        ####
        self.bathy_interp = NearestNDInterpolator(
            list(zip(bathymetry[:, 0], bathymetry[:, 1])), bathymetry[:, 2]
        )

    def update_graph(self):
        if not os.path.exists(self.args.datapath):
            return
        # print(pos.shape, edges.shape, colors.shape)
        pos, edges, solution_path, costs = get_latest_pdata(
            self.args, self.z_scaler, self.cost_idx
        )
        # print(pos.shape, edges.shape, colors.shape)

        if self.args.graph:
            # colors = colormap.map(costs)
            if self.offset is not None:
                pos += self.offset

            #################################################
            #################################################

            if self.args.use_ci:
                _mean, _min, _max = mean_confidence_interval(costs)
            else:
                _min = costs.min()
                _max = costs.max()

            _min = 0
            if self.args.min is not None:
                _min = self.args.min
            if self.args.max is not None:
                _max = self.args.max

            if np.isnan(_max):
                _max = np.nanmax(costs[costs != np.inf])
            if np.isnan(_min):
                _min = np.nanmin(costs[costs != -np.inf])

            costs = np.clip(costs, _min, _max)
            costs = (costs - _min) / (_max - _min)

            # costs = costs - _min
            #################################################
            #################################################

            colors = self.args.colormap.map(costs)  # [:-2]

            self.lines.set_data(pos=pos, connect=edges, color=colors)
            self.args.cbar_widget.clim = (_min, _max)
            # markers.set_data(pos=pos, face_color=colors)
        else:
            self.lines.set_data(
                pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR
            )
            self.args.cbar_widget.clim = (np.nan, np.nan)

        if not self.had_set_range:
            self.args.view.camera.set_range()
            self.had_set_range = True

            axis_len = 100

            _pos = np.array(
                [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1]],
                dtype=np.float,
            )

            _pos *= self.args.principle_axis_length

            _pos += pos.min(0)

            _pos[:, 2] -= self.args.principle_axis_z_offset

            self.axis_visual = XYZAxis(
                pos=_pos,
                parent=self.args.view.scene,
                width=5,
            )

            # _duplicated_solution_path = np.empty((solution_path.shape[0] * 2, solution_path.shape[1]), dtype=solution_path.dtype)
            # _duplicated_solution_path[solution_path.shape[0]:, :] = solution_path
            # _duplicated_solution_path[:solution_path.shape[0], :] = solution_path
            # _duplicated_solution_path[:solution_path.shape[0], 2] += 100000

            # self.sol_lines.set_data(pos=_duplicated_solution_path)

        self.sol_lines.set_path(solution_path)
        if self.args.extra_sol:
            fake_solution_path = solution_path.copy()
            self.fake_sol_lines.set_path(fake_solution_path)

        vertices = []
        faces = []

        try:
            keepout_zones = get_keepout_zones(self.args, self.bathy_interp)
            for k in keepout_zones:
                k.depth = min(k.depth, self.avg_ocean_depth)

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
            self.z_scaler(vertices)

            self.keepout_zone_mesh.set_data(
                vertices=vertices,
                faces=np.array(faces),
            )
