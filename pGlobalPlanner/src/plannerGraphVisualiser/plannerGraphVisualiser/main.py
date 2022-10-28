from itertools import chain

import vispy.io.stl
from vispy import app, scene, color
import argparse

import os

from plannerGraphVisualiser.visualisable_planner_graph_moos import (
    VisualisablePlannerGraphWithMossMsg,
)

os.putenv("NO_AT_BRIDGE", "1")

from vispy.color import get_colormap, Color

from plannerGraphVisualiser.abstract_visualisable_plugin import ToggleableMixin
from plannerGraphVisualiser.visualisable_axis import VisualisablePrincipleAxis
from plannerGraphVisualiser.visualisable_bathymetry import VisualisableBathy
from plannerGraphVisualiser.visualisable_koz import VisualisableKOZ
from plannerGraphVisualiser.visualisable_moos_swarm import (
    VisualisableMoosSwarm,
    SwarmModelType,
)
from plannerGraphVisualiser.visualisable_ocean_currents import VisualisableOceanCurrent
from plannerGraphVisualiser.visualisable_planner_graph import VisualisablePlannerGraph
from .visualiser import Visualiser


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


import argparse

from vispy import app, scene
from vispy.io import read_mesh, load_data_file
from vispy.scene.visuals import Mesh
from vispy.scene import transforms
from vispy.visuals.filters import ShadingFilter, WireframeFilter

#
# parser = argparse.ArgumentParser()
# # default_mesh = load_data_file('sub.obj')
# # default_mesh = load_data_file('orig/triceratops.obj.gz')
# # parser.add_argument('--mesh', default=default_mesh)
# parser.add_argument('--shininess', default=100)
# parser.add_argument('--wireframe-width', default=1)
# args, _ = parser.parse_known_args()
#
# # vertices, faces, normals, texcoords = read_mesh(args.mesh)
# # vertices, faces, normals, texcoords = read_mesh("sub.obj.gz")
# # vertices, faces, normals, texcoords = read_mesh("/home/tin/Downloads/repaired.obj")
# # vertices, faces, normals, texcoords = read_mesh("/home/tin/11098_submarine_v4.obj")
#
# with open("/home/tin/Downloads/floating_submarine.stl", 'rb') as f:
#     data = vispy.io.stl.load_stl(f)
# vertices, faces, normals = data['vertices'], data['faces'], data['face_normals']
#
#
#
# canvas = scene.SceneCanvas(keys='interactive', bgcolor='white')
# view = canvas.central_widget.add_view()
#
# view.camera = 'arcball'
# view.camera.depth_value = 1e3
#
# # Create a colored `MeshVisual`.
# mesh = Mesh(vertices, faces, color=(.5, .7, .5, 1))
# mesh.transform = transforms.MatrixTransform()
# # mesh.transform.rotate(90, (1, 0, 0))
# # mesh.transform.rotate(-45, (0, 0, 1))
# mesh.transform.scale([0.1]*3)
# view.add(mesh)
#
# # Use filters to affect the rendering of the mesh.
# wireframe_filter = WireframeFilter(width=args.wireframe_width)
# # Note: For convenience, this `ShadingFilter` would be created automatically by
# # the `MeshVisual with, e.g. `mesh = MeshVisual(..., shading='smooth')`. It is
# # created manually here for demonstration purposes.
# shading_filter = ShadingFilter(shininess=args.shininess)
# # The wireframe filter is attached before the shading filter otherwise the
# # wireframe is not shaded.
# mesh.attach(wireframe_filter)
# mesh.attach(shading_filter)
#
#
# def attach_headlight(view):
#     light_dir = (0, 1, 0, 0)
#     shading_filter.light_dir = light_dir[:3]
#     initial_light_dir = view.camera.transform.imap(light_dir)
#
#     @view.scene.transform.changed.connect
#     def on_transform_change(event):
#         transform = view.camera.transform
#         shading_filter.light_dir = transform.map(initial_light_dir)[:3]
#
#
# attach_headlight(view)
#
# shading_states = (
#     dict(shading=None),
#     dict(shading='flat'),
#     dict(shading='smooth'),
# )
# shading_state_index = shading_states.index(
#     dict(shading=shading_filter.shading))
#
# wireframe_states = (
#     dict(wireframe_only=False, faces_only=False,),
#     dict(wireframe_only=True, faces_only=False,),
#     dict(wireframe_only=False, faces_only=True,),
# )
# wireframe_state_index = wireframe_states.index(dict(
#     wireframe_only=wireframe_filter.wireframe_only,
#     faces_only=wireframe_filter.faces_only,
# ))
#
#
# def cycle_state(states, index):
#     new_index = (index + 1) % len(states)
#     return states[new_index], new_index
#
#
# @canvas.events.key_press.connect
# def on_key_press(event):
#     global shading_state_index
#     global wireframe_state_index
#     if event.key == 's':
#         state, shading_state_index = cycle_state(shading_states,
#                                                  shading_state_index)
#         for attr, value in state.items():
#             setattr(shading_filter, attr, value)
#         mesh.update()
#     elif event.key == 'w':
#         wireframe_filter.enabled = not wireframe_filter.enabled
#         mesh.update()
#     elif event.key == 'f':
#         state, wireframe_state_index = cycle_state(wireframe_states,
#                                                    wireframe_state_index)
#         for attr, value in state.items():
#             setattr(wireframe_filter, attr, value)
#         mesh.update()
#
#
# canvas.show()
#
#
# if __name__ == "__main__":
#     app.run()


if __name__ == "__main__":
    if not args.no_monitor:
        try:
            print("launching ocean current viewer")
            from .msg_monitor import pGlobalPlannerMonitor

            moos_app = pGlobalPlannerMonitor()
            # moos_app.spin()
        except Exception as e:
            print(e)
    run()
