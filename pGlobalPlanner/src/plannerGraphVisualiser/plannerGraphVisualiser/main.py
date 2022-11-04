import os
import argparse
from vispy import app, scene

from plannerGraphVisualiser.easy_visualiser.plugins.visualisable_status_bar import (
    VisualisableStatusBar,
)
from plannerGraphVisualiser.visualisable_axis_with_bathy_offset import (
    VisualisablePrincipleAxisWithBathyOffset,
)
from plannerGraphVisualiser.visualisable_planner_graph_moos import (
    VisualisablePlannerGraphWithMossMsg,
)

os.putenv("NO_AT_BRIDGE", "1")

from plannerGraphVisualiser.easy_visualiser.plugins.visualisable_axis import (
    VisualisablePrincipleAxis,
)
from plannerGraphVisualiser.visualisable_bathymetry import VisualisableBathy
from plannerGraphVisualiser.visualisable_koz import VisualisableKOZ
from plannerGraphVisualiser.visualisable_moos_swarm import (
    VisualisableMoosSwarm,
    SwarmModelType,
)
from plannerGraphVisualiser.visualisable_ocean_currents import VisualisableOceanCurrent
from plannerGraphVisualiser.visualisable_planner_graph import VisualisablePlannerGraph
from .easy_visualiser.visualiser import Visualiser

import subprocess
import sys

try:
    from tap import Tap
except ModuleNotFoundError:

    def install(package):
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    install("typed-argument-parser")
    from tap import Tap


class ToggleableBool:
    def __init__(self, value: bool = True):
        self.value: bool = value

    def __bool__(self) -> bool:
        return self.value

    def __repr__(self):
        return "bool"


class PlannerVisualiserArgParser(Tap):
    datapath: str
    depth_datapath: str = "/tmp/depth_points.npy"
    current_datapath: str = "/tmp/ocean_currents.npy"
    colormap: str = "plasma"
    extra_sol: ToggleableBool = True
    use_ci: bool = True
    """
    use 95 confident interval for setting cost limit (to avoid being overwhelmed by extremely high cost value)
    """
    min: float = None
    max: float = None
    z_scale_factor: float = 40
    principle_axis_z_offset: float = 1000
    principle_axis_length: float = 100000
    no_monitor: bool = True
    swarm_model_type: str = SwarmModelType.auv.name
    graph: bool = False  # show rrt graph
    graph_solution: bool = True  # show rrt graph solution
    currents: bool = True  # show ocean current
    bathymetry: bool = True  # show bathymetry
    bathymetry_colour_scale: bool = True  # show bathymetry with colour scale

    def configure(self):
        self.add_argument(
            "datapath",
            metavar="DATA",
            type=str,
            nargs="?",
            default="/tmp/pGlobalPlannerGraph.npz",
        )
        self.add_argument(
            "--swarm-model-type",
            choices=[SwarmModelType.auv.name, SwarmModelType.simple_sphere.name],
            default=SwarmModelType.auv.name,
        )


args = PlannerVisualiserArgParser(underscores_to_dashes=True).parse_args()
if not args.graph:
    args.extra_sol = False


def run():
    global args

    # Display the data
    canvas = scene.SceneCanvas(
        title="pGlobalPlanner Plan Visualiser", keys="interactive", show=True
    )
    args.canvas = canvas

    view = canvas.central_widget.add_view()
    view.camera = "turntable"
    view.camera.aspect = 1

    args.view = view

    args.vis = Visualiser(args)
    args.vis.register_plugin(VisualisableStatusBar(args))
    args.vis.register_plugin(VisualisableBathy(args))
    args.vis.register_plugin(VisualisablePlannerGraph(args))
    args.vis.register_plugin(VisualisableKOZ(args))
    args.vis.register_plugin(
        VisualisablePrincipleAxisWithBathyOffset(
            args, axis_length=args.principle_axis_length
        )
    )
    args.vis.register_plugin(VisualisableOceanCurrent(args))
    args.vis.register_plugin(VisualisableMoosSwarm(args))
    args.vis.register_plugin(VisualisablePlannerGraphWithMossMsg(args))
    args.vis.initialise()

    from ._impl import update

    timer = app.Timer(interval=1, connect=lambda ev: update(args, ev), start=True)

    update(args, None)
    app.run()


if __name__ == "__main__":
    # if not args.no_monitor:
    #     try:
    #         print("launching ocean current viewer")
    #         from .msg_monitor import pGlobalPlannerMonitor
    #
    #         moos_app = pGlobalPlannerMonitor()
    #         # moos_app.spin()
    #     except Exception as e:
    #         print(e)
    run()
