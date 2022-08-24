from vispy import app, scene, color
import argparse

from vispy.color import get_colormap, Color
from .graph_visualiser import GraphVisualiser


def parse_args():
    parser = argparse.ArgumentParser(description="pGlobalPlannerVisualiser.")
    parser.add_argument(
        "datapath",
        metavar="DATA",
        type=str,
        nargs="?",
        default="/tmp/pGlobalPlannerGraph.npz",
    )
    parser.add_argument("--colormap", default="plasma")
    parser.add_argument("--no-extra-sol", dest="extra_sol", action="store_false")
    parser.add_argument("--min", type=float)
    parser.add_argument("-m", "--max", type=float)
    parser.add_argument("-c", "--cost-index", type=int)
    parser.add_argument("-z", "--z-scale-factor", type=float, default=40)

    return parser.parse_args()


args = parse_args()


def run():
    global args

    # Display the data
    canvas = scene.SceneCanvas(
        title="pGlobalPlanner Plan Visualiser", keys="interactive", show=True
    )
    view = canvas.central_widget.add_view()
    view.camera = "turntable"
    view.camera.aspect = 1

    args.view = view

    # colormap = get_colormap("viridis")
    # colormap = get_colormap("jet")
    # colormap = get_colormap("plasma")
    args.colormap = get_colormap(args.colormap)

    last_modify_time = None

    cbar_widget = scene.ColorBarWidget(
        label="Cost",
        clim=(0, 99),
        cmap=args.colormap,
        orientation="right",
        border_width=1,
        label_color="#ffffff",
    )
    cbar_widget.border_color = "#212121"
    args.cbar_widget = cbar_widget

    grid = canvas.central_widget.add_grid(margin=10)

    # col num just to make it on the right size (0 is left)
    grid.add_widget(col=10)
    grid.add_widget(cbar_widget, col=0)

    args.vis = []
    args.vis.append(
        GraphVisualiser(args, "all" if args.cost_index is None else args.cost_index)
    )
    # vis = GraphVisualiser(cbar_widget, 0)
    # vis2 = GraphVisualiser(cbar_widget, 1, np.array([-300000, 0, 0]))


    from ._impl import update

    timer = app.Timer(interval=1, connect=lambda ev: update(args, ev), start=True)

    update(args, None)
    app.run()


if __name__ == "__main__":
    run()
