import json
import numpy as np

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)
from plannerGraphVisualiser.moos_comms import pMoosPlannerVisualiser
from plannerGraphVisualiser.visualisable_planner_graph import SolutionLine

PLAN_VARIABLE = "GLOBAL_PLAN"


class VisualisablePlannerGraphWithMossMsg(
    VisualisablePlugin,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sol_lines = SolutionLine(self.args.view.scene, color="cyan")
        self.moos = pMoosPlannerVisualiser.get_instance()
        self.moos.register_variable(PLAN_VARIABLE, self.__plan_msg_cb)

    @property
    def name(self):
        return "moos_plan"

    def __plan_msg_cb(self, msg):
        data = json.loads(msg.string())
        path = np.stack([data["x"], data["y"], data["z"]]).T
        path[:, 2] = self.args.z_scaler(path[:, 2])
        self.sol_lines.set_path(path)
