import json
from typing import TYPE_CHECKING

import numpy as np

from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.plugins.ext.visualisable_planner_graph import SolutionLine

PLAN_VARIABLE = "GLOBAL_PLAN"

if TYPE_CHECKING:
    from easy_visualiser.input.moos import MoosComm


class VisualisablePlannerGraphWithMossMsg(
    VisualisablePlugin,
):
    sol_lines: SolutionLine
    moos: "MoosComm"

    def construct_plugin(self) -> bool:
        super().construct_plugin()

        from easy_visualiser.input.moos import MoosComm

        self.moos = MoosComm.get_instance()
        self.moos.register_variable(PLAN_VARIABLE, self.__plan_msg_cb)
        self.sol_lines = SolutionLine(self.visualiser.visual_parent, color="cyan")
        return True

    @property
    def name(self):
        return "moos_plan"

    def __plan_msg_cb(self, msg):
        data = json.loads(msg.string())
        path = np.stack([data["x"], data["y"], data["z"]]).T
        path[:, 2] = self.other_plugins.zscaler.scaler(path[:, 2])
        self.sol_lines.set_path(path)
