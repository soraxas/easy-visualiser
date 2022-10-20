import os
from typing import Tuple, Optional, Dict, Callable

import numpy as np
from plannerGraphVisualiser import get_latest_pdata, mean_confidence_interval
from vispy import scene

from plannerGraphVisualiser.abstract_visualisable_plugin import (
    VisualisablePlugin,
    ToggleableMixin,
    FileModificationGuardableMixin,
    UpdatableMixin,
)
from plannerGraphVisualiser.dummy import (
    DUMMY_AXIS_VAL,
    DUMMY_LINE,
    DUMMY_CONNECT,
    DUMMY_COLOUR,
)


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


class VisualisablePlannerGraph(
    FileModificationGuardableMixin, ToggleableMixin, UpdatableMixin, VisualisablePlugin
):
    lines = None
    __had_set_range: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.keys = [
            ("g", "toggle planner graph", self.__toggle_graph_cb),
            ("c", "switch cost index", self.__switch_cost_cb),
        ]
        self.sol_lines = SolutionLine(self.args.view.scene)
        # if self.args.extra_sol:
        self.fake_sol_lines = SolutionLine(self.args.view.scene, offset=200000)

    def __toggle_graph_cb(self):
        self.args.graph = not self.args.graph
        self.args.extra_sol = not self.args.graph
        # print(self.args.extra_sol)
        self.toggle()

    @property
    def name(self):
        return "gplanner graph"

    @property
    def target_file(self):
        return self.args.datapath

    def construct_plugin(self) -> None:
        super().construct_plugin()
        self.args.extra_sol = not self.args.graph
        self.lines = scene.Line(
            antialias=False, method="gl", parent=self.args.view.scene, width=3
        )
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.args.cbar_widget.clim = (np.nan, np.nan)

    def __switch_cost_cb(self) -> None:
        if self.args.cost_index is None:
            self.args.cost_index = 0
        else:
            self.args.cost_index += 1
        self._last_modify_time = None
        self.update()

    def __construct_graph(self, pos, edges, costs) -> None:
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
        if _max == _min:
            costs[:] = np.nan
        else:
            costs = (costs - _min) / (_max - _min)

        # costs = costs - _min
        #################################################
        #################################################

        colors = self.args.colormap.map(costs)  # [:-2]

        self.lines.set_data(pos=pos, connect=edges, color=colors)
        self.args.cbar_widget.clim = (_min, _max)

    def __construct_solution(self, solution_path) -> None:
        self.sol_lines.set_path(solution_path)
        if self.args.extra_sol:
            fake_solution_path = solution_path.copy()
            self.fake_sol_lines.set_path(fake_solution_path)
        else:
            self.fake_sol_lines.set_path([])

    def turn_on_plugin(self):
        super().turn_on_plugin()
        pos, edges, solution_path, costs = get_latest_pdata(self.args)

        self.__construct_graph(pos, edges, costs)
        self.__construct_solution(solution_path)

    def turn_off_plugin(self):
        super().turn_off_plugin()
        self.lines.set_data(pos=DUMMY_LINE, connect=DUMMY_CONNECT, color=DUMMY_COLOUR)
        self.args.cbar_widget.clim = (np.nan, np.nan)

        self.fake_sol_lines.set_path([])

    def on_update(self):
        self.turn_on_plugin()
        self.__set_range()

    def __set_range(self):
        if not self.__had_set_range:
            self.args.view.camera.set_range()
            self.__had_set_range = True