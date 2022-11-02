import os
import argparse
from vispy import app, scene

from plannerGraphVisualiser.visualisable_planner_graph_moos import (
    VisualisablePlannerGraphWithMossMsg,
)

os.putenv("NO_AT_BRIDGE", "1")

from plannerGraphVisualiser.visualisable_axis import VisualisablePrincipleAxis
from plannerGraphVisualiser.visualisable_bathymetry import VisualisableBathy
from plannerGraphVisualiser.visualisable_koz import VisualisableKOZ
from plannerGraphVisualiser.visualisable_moos_swarm import (
    VisualisableMoosSwarm,
    SwarmModelType,
)
from plannerGraphVisualiser.visualisable_ocean_currents import VisualisableOceanCurrent
from plannerGraphVisualiser.visualisable_planner_graph import VisualisablePlannerGraph
from .easy_visualiser.visualiser import Visualiser


def parse_args():
    parser = argparse.ArgumentParser(description="pGlobalPlannerVisualiser.")
    parser.add_argument(
        "datapath",
        metavar="DATA",
        type=str,
        nargs="?",
        default="/tmp/pGlobalPlannerGraph.npz",
    )
    parser.add_argument(
        "--depth-datapath",
        type=str,
        default="/tmp/depth_points.npy",
    )
    parser.add_argument(
        "--current-datapath",
        type=str,
        default="/tmp/ocean_currents.npy",
    )
    parser.add_argument("--colormap", default="plasma")
    parser.add_argument("--no-extra-sol", dest="extra_sol", action="store_false")
    parser.add_argument(
        "--no-ci",
        dest="use_ci",
        help="use 95 confident interval for setting cost limit (to avoid being overwhelmed by extremely high cost value)",
        action="store_false",
    )
    parser.add_argument("--min", type=float)
    parser.add_argument("-m", "--max", type=float)
    parser.add_argument("-c", "--cost-index", type=int)
    parser.add_argument("-z", "--z-scale-factor", type=float, default=40)
    parser.add_argument("--principle-axis-z-offset", type=float, default=1000)
    parser.add_argument("--principle-axis-length", type=float, default=100000)
    parser.add_argument("--no-monitor", action="store_true")
    parser.add_argument(
        "--swarm-model-type",
        choices=[SwarmModelType.auv.name, SwarmModelType.simple_sphere.name],
        default=SwarmModelType.auv.name,
    )
    parser.add_argument("-g", "--graph", action="store_true", help="show rrt graph")
    parser.add_argument(
        "--graph-solution",
        action="store_true",
        help="show rrt graph solution",
        default=True,
    )
    parser.add_argument(
        "--currents", action="store_true", help="show ocean current", default=True
    )
    parser.add_argument(
        "--bathymetry", action="store_true", help="show bathymetry", default=True
    )
    parser.add_argument(
        "--bathymetry-colour-scale",
        action="store_true",
        help="show bathymetry with colour scale",
        default=True,
    )

    return parser.parse_args()


args = parse_args()
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
    args.vis.register_plugin(VisualisableBathy)
    args.vis.register_plugin(VisualisablePlannerGraph)
    args.vis.register_plugin(VisualisableKOZ)
    args.vis.register_plugin(VisualisablePrincipleAxis)
    args.vis.register_plugin(VisualisableOceanCurrent)
    args.vis.register_plugin(VisualisableMoosSwarm)
    args.vis.register_plugin(VisualisablePlannerGraphWithMossMsg)
    args.vis.initialise()

    # grid.add_widget(
    #     scene.Label(
    #         "\n".join(
    #             "Press [{key}] to {functionality}".format(
    #                 key=cb[0], functionality=cb[1]
    #             )
    #             for cb in chain(
    #                 *(
    #                     p.keys
    #                     for p in args.vis.plugins
    #                     if isinstance(p, ToggleableMixin)
    #                 )
    #             )
    #         ),
    #         color="white",
    #         anchor_x="left",
    #         anchor_y="bottom",
    #         pos=[0, 0],
    #     ),
    #     col=0,
    #     row=8,
    #     row_span=2,
    # )

    # vis = GraphVisualiser(cbar_widget, 0)
    # vis2 = GraphVisualiser(cbar_widget, 1, np.array([-300000, 0, 0]))

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
