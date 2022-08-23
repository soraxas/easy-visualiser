from vispy import app, scene, color
import numpy as np
import scipy
from vispy.visuals.colorbar import ColorBarVisual
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

    def update(self):

        # print(pos.shape, edges.shape, colors.shape)
        pos, edges, solution_path, costs = get_latest_pdata(self.cost_idx)
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
        # _max = 20000000
        # _max = 5000000
        if self.args.min is not None:
            _min = self.args.min
        if self.args.max is not None:
            _max = self.args.max

        costs = np.clip(costs, _min, _max)
        costs = (costs - _min) / (_max - _min)
        # costs = costs - _min
        #################################################
        #################################################

        colors = self.args.colormap.map(costs)  # [:-2]

        self.lines.set_data(pos=pos, connect=edges, color=colors)
        self.args.cbar_widget.clim = (_min, _max)
        # markers.set_data(pos=pos, face_color=colors)

        if last_modify_time is None:
            self.args.view.camera.set_range()

        # if len(solution_path) > 0:
        if self.sol_lines is None:
            self.sol_lines = scene.Line(
                connect="strip",
                antialias=False,
                method="gl",
                # method='agg',
                parent=self.args.view.scene,
                width=50,
                color="red",
            )

            if self.args.extra_sol:
                self.fake_sol_lines = scene.Line(
                    connect="strip",
                    antialias=False,
                    method="gl",
                    # method='agg',
                    parent=self.args.view.scene,
                    width=50,
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
