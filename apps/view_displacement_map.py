import os

from tap import Tap

from easy_visualiser.plugins.functional_alternative_vis import AlternativeVisTrigger
from easy_visualiser.plugins.visualisable_displacementmap import (
    VisualisableDisplacementMap,
)
from easy_visualiser.plugins.visualisable_displacementmap_glob import (
    VisualisableDisplacementMapLoopWithGlob,
)
from easy_visualiser.plugins.visualisable_mesh import VisualisableMesh
from easy_visualiser.plugins.visualisable_status_bar import VisualisableStatusBar
from easy_visualiser.utils.triggerable_utils import (
    move_triggerable_plugin_keys_to_nested_modal_control,
)
from easy_visualiser.visualiser import Visualiser

os.putenv("NO_AT_BRIDGE", "1")


class DisplacementMapArgParser(Tap):
    image_path: str
    glob: bool = False

    def configure(self):
        self.add_argument(
            "image_path",
            type=str,
        )


def run():
    args = DisplacementMapArgParser(underscores_to_dashes=True).parse_args()

    visualiser = Visualiser(
        title="Displacement Map Visualiser",
    )
    visualiser.register_plugin(VisualisableStatusBar())
    if args.glob:
        displacement_plugin = VisualisableDisplacementMapLoopWithGlob(args.image_path)
        visualiser.register_plugin(displacement_plugin)

    else:
        visualiser.register_plugin(
            move_triggerable_plugin_keys_to_nested_modal_control(
                VisualisableDisplacementMap(args.image_path),
                key="d",
                modal_name="displacement map",
            )
        )
        visualiser.register_plugin(
            move_triggerable_plugin_keys_to_nested_modal_control(
                VisualisableMesh(args.image_path),
                key="m",
                modal_name="mesh",
            )
        )

        def construct_cb(_plugin):
            # sync the scale
            _plugin.other_plugins.VisualisableMesh._z_scale = (
                _plugin.other_plugins.VisualisableDisplacementMap._z_scale
            )

            _plugin.other_plugins.VisualisableMesh.turn_off_plugin()
            _plugin.other_plugins.VisualisableDisplacementMap.turn_on_plugin()

        def toggle_cb(_plugin):
            _plugin.other_plugins.VisualisableMesh.toggle()
            _plugin.other_plugins.VisualisableDisplacementMap.toggle()

        visualiser.register_plugin(
            AlternativeVisTrigger(
                construct_callback=construct_cb,
                toggle_callback=toggle_cb,
            ),
            depends_on={"VisualisableMesh", "VisualisableDisplacementMap"},
        )

    visualiser.initialise()

    visualiser.run(regular_update_interval=1)


if __name__ == "__main__":
    run()
