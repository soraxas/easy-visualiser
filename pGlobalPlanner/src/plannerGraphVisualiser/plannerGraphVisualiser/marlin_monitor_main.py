import os

from plannerGraphVisualiser.easy_visualiser.plugins.functional_zscaler import (
    AxisScalerPlugin,
)
from plannerGraphVisualiser.visualisable_axis_ruler import (
    VisualisableAxisRuler,
)
from plannerGraphVisualiser.easy_visualiser.plugins.visualisable_status_bar import (
    VisualisableStatusBar,
)
from plannerGraphVisualiser.easy_visualiser.utils import ToggleableBool
from plannerGraphVisualiser.visualisable_axis_with_bathy_offset import (
    VisualisablePrincipleAxisWithBathyOffset,
)
from plannerGraphVisualiser.visualisable_planner_graph_moos import (
    VisualisablePlannerGraphWithMossMsg,
)

os.putenv("NO_AT_BRIDGE", "1")

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


class PlannerVisualiserArgParser(Tap):
    datapath: str
    depth_datapath: str = "/tmp/depth_points.npy"
    current_datapath: str = "/tmp/ocean_currents.npy"
    colormap: str = "plasma"
    extra_sol = ToggleableBool(True)
    use_ci = ToggleableBool(True)
    """
    use 95 confident interval for setting cost limit (to avoid being overwhelmed by extremely high cost value)
    """
    min: float = None
    max: float = None
    z_scale_factor: float = 40
    principle_axis_z_offset: float = 1000
    principle_axis_length: float = 100000
    no_monitor = ToggleableBool(True)
    no_moos: bool = False
    swarm_model_type: str = SwarmModelType.auv.name
    graph = ToggleableBool(False)  # show rrt graph
    graph_solution = ToggleableBool(True)  # show rrt graph solution
    currents = ToggleableBool(True)  # show ocean current
    bathymetry = ToggleableBool(True)  # show bathymetry
    bathymetry_colour_scale = ToggleableBool(True)  # show bathymetry with colour scale

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


def run():
    args = PlannerVisualiserArgParser(underscores_to_dashes=True).parse_args()
    if not args.graph:
        args.extra_sol.set(False)

    visualiser = Visualiser(
        title="pGlobalPlanner Plan Visualiser",
    )
    visualiser.register_plugin(AxisScalerPlugin(args.z_scale_factor, name="zscaler"))
    visualiser.register_plugin(VisualisableStatusBar())
    visualiser.register_plugin(
        VisualisableBathy(
            bathy_toggle=args.bathymetry,
            bathy_colorscale_toggle=args.bathymetry_colour_scale,
            depth_datapath=args.depth_datapath,
        )
    )
    visualiser.register_plugin(
        VisualisablePlannerGraph(
            graph_data_path=args.datapath,
            graph_toggle=args.graph,
            graph_solution_toggle=args.graph_solution,
            graph_solution_extra_toggle=args.extra_sol,
            colormap=args.colormap,
        )
    )
    visualiser.register_plugin(VisualisableKOZ(graph_data_path=args.datapath))
    visualiser.register_plugin(
        VisualisablePrincipleAxisWithBathyOffset(axis_length=args.principle_axis_length)
    )
    visualiser.register_plugin(
        VisualisableAxisRuler(), depends_on=["bathymetry", "zscaler"]
    )
    visualiser.register_plugin(
        VisualisableOceanCurrent(
            ocean_current_toggle=args.currents,
            ocean_current_datapath=args.current_datapath,
        )
    )
    if not args.no_moos:
        visualiser.register_plugin(
            VisualisableMoosSwarm(swarm_model_type=args.swarm_model_type)
        )
        visualiser.register_plugin(VisualisablePlannerGraphWithMossMsg())
    visualiser.initialise()

    visualiser.run(regular_update_interval=1)


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
