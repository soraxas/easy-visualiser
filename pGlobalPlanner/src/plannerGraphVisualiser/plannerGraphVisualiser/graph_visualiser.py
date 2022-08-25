from vispy import app, scene, color
import numpy as np
import scipy
from vispy.visuals.colorbar import ColorBarVisual
from vispy.scene.visuals import XYZAxis
from ._impl import *


class GraphVisualiser:
    def __init__(self, args, cost_idx="all", offset=None):
        self.args = args
        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.args.view.scene, width=3
        )
        self.cost_idx = cost_idx

        self.offset = offset

        self.sol_lines = None
        self.fake_sol_lines = None

        self.start_markers = None
        self.goal_markers = None
        self.axis_visual = None

        self.had_set_range = False

    def update(self):

        # print(pos.shape, edges.shape, colors.shape)
        pos, edges, solution_path, costs = get_latest_pdata(self.args, self.cost_idx)
        # print(pos.shape, edges.shape, colors.shape)

        # colors = colormap.map(costs)
        if self.offset is not None:
            pos += self.offset

        #################################################
        #################################################
        use_ci = True
        use_ci = False
        if use_ci:
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
            _max = np.nanmax(costs)
        if np.isnan(_min):
            _min = np.nanmax(costs)

        costs = np.clip(costs, _min, _max)
        costs = (costs - _min) / (_max - _min)
        # costs = costs - _min
        #################################################
        #################################################

        colors = self.args.colormap.map(costs)  # [:-2]

        self.lines.set_data(pos=pos, connect=edges, color=colors)
        self.args.cbar_widget.clim = (_min, _max)
        # markers.set_data(pos=pos, face_color=colors)

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

        # if len(solution_path) > 0:
        if self.sol_lines is None:
            self.sol_lines = scene.Line(
                connect="strip",
                antialias=False,
                method="gl",
                # method='agg',
                parent=self.args.view.scene,
                width=5,
                color="red",
            )

            if self.args.extra_sol:
                self.fake_sol_lines = scene.Line(
                    connect="strip",
                    antialias=False,
                    method="gl",
                    # method='agg',
                    parent=self.args.view.scene,
                    width=5,
                    color="red",
                )

            # _duplicated_solution_path = np.empty((solution_path.shape[0] * 2, solution_path.shape[1]), dtype=solution_path.dtype)
            # _duplicated_solution_path[solution_path.shape[0]:, :] = solution_path
            # _duplicated_solution_path[:solution_path.shape[0], :] = solution_path
            # _duplicated_solution_path[:solution_path.shape[0], 2] += 100000

            # self.sol_lines.set_data(pos=_duplicated_solution_path)
        self.sol_lines.set_data(pos=solution_path)

        if self.args.extra_sol:
            fake_solution_path = solution_path.copy()
            if len(solution_path) > 0:
                fake_solution_path[:, -1] -= 200000
            self.fake_sol_lines.set_data(pos=fake_solution_path)
