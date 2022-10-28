import json
import os
from typing import Tuple, Optional, Dict, Callable

import numpy as np
from plannerGraphVisualiser import get_latest_pdata, mean_confidence_interval
from vispy import scene

from plannerGraphVisualiser.abstract_visualisable_plugin import (
    VisualisablePlugin,
    ToggleableMixin,
    UpdatableMixin,
    CallableAndFileModificationGuardableMixin,
)
from plannerGraphVisualiser.dummy import (
    DUMMY_AXIS_VAL,
    DUMMY_LINE,
    DUMMY_CONNECT,
    DUMMY_COLOUR,
)
from plannerGraphVisualiser.modal_control import ModalControl
from plannerGraphVisualiser.moos_comms import pMoosPlannerVisualiser


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
            color="cyan",
        )

    def set_path(self, _path):
        if len(_path) <= 0:
            _path = DUMMY_LINE
        else:
            if self.offset:
                _path[:, -1] -= self.offset
        self.line_visual.set_data(pos=_path)


PLAN_VARIABLE = "GLOBAL_PLAN"


class VisualisablePlannerGraphWithMossMsg(
    VisualisablePlugin,
):
    lines = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guarding_callable = lambda: True

        self.sol_lines = SolutionLine(self.args.view.scene)
        self.moos = pMoosPlannerVisualiser.get_instance()
        self.moos.register_variable(PLAN_VARIABLE, self.__plan_msg_cb)

    def __toggle_graph_cb(self):
        self.args.graph = not self.args.graph
        self.args.extra_sol = not self.args.graph
        self.toggle()

    @property
    def name(self):
        return "moos_plan"

    def __plan_msg_cb(self, msg):
        data = json.loads(msg.string())
        path = np.stack([data["x"], data["y"], data["z"]]).T
        path[:, 2] = self.args.z_scaler(path[:, 2])
        self.sol_lines.set_path(path)

    def construct_plugin(self) -> None:
        super().construct_plugin()

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
        if self.args.extra_sol and self.args.graph:
            fake_solution_path = solution_path.copy()
            self.fake_sol_lines.set_path(fake_solution_path)
        else:
            self.fake_sol_lines.set_path([])

    def turn_on_plugin(self):
        super().turn_on_plugin()

    def turn_off_plugin(self):
        super().turn_off_plugin()
        # self.sol_lines.set_path()
