import os

import glob
import numpy as np
from PIL import Image
from vispy.color import get_colormap

from plannerGraphVisualiser.easy_visualiser.dummy import DUMMY_AXIS_VAL
from plannerGraphVisualiser.easy_visualiser.key_mapping import (
    Mapping,
    Key,
    DummyMappingLine,
)
from plannerGraphVisualiser.easy_visualiser.modal_control import ModalControl
from plannerGraphVisualiser.easy_visualiser.plugin_capability import (
    TriggerableMixin,
    ToggleableMixin,
    IntervalUpdatableMixin,
)
from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)
from plannerGraphVisualiser.easy_visualiser.plugins.visualisable_points import (
    VisualisablePoints,
)
from plannerGraphVisualiser.easy_visualiser.plugins.visualisable_status_bar import (
    VisualisableStatusBar,
)
from plannerGraphVisualiser.easy_visualiser.utils import (
    ScalableFloat,
    map_array_to_0_1,
    IncrementableInt,
)
from plannerGraphVisualiser.easy_visualiser.visuals.gridmesh import FixedGridMesh

from .easy_visualiser.visualiser import Visualiser

import subprocess
import sys

os.putenv("NO_AT_BRIDGE", "1")

try:
    from tap import Tap
except ModuleNotFoundError:

    def install(package):
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    install("typed-argument-parser")
    from tap import Tap


class DisplacementMapArgParser(Tap):
    image_path: str
    glob: bool = False

    def configure(self):
        self.add_argument(
            "image_path",
            type=str,
        )


class VisualisableMesh(ToggleableMixin, TriggerableMixin, VisualisablePlugin):
    def __init__(self, image_path: str):
        super().__init__()
        self._marker_scale = ScalableFloat(1, upper_bound=50)
        self._antialias = ScalableFloat(0.25, upper_bound=10)

        self.keys = [
            Mapping("z", "reset zoom", lambda: self.set_range()),
        ]
        self._z_scale = ScalableFloat(0.3, upper_bound=10)
        with Image.open(image_path) as im:
            self.z_data = np.array(im.convert("L"))
            self.z_data_ = self.z_data
        self.grid = np.indices(self.z_data.shape)
        self.z_data = self.z_data.ravel()
        point_data = np.vstack(
            [
                self.grid[0].ravel(),
                self.grid[1].ravel(),
                self.z_data * float(self._z_scale),
            ],
        ).T

        __scale_factor = 1.25
        self.grid_every = IncrementableInt(1, lower_bound=1)

        self.keys[:0] = [
            DummyMappingLine(lambda: f"scale: {float(self._z_scale):.2f}"),
            Mapping(
                Key.Plus,
                "Increase mesh typology scale",
                lambda: self._z_scale.scale(__scale_factor) and self._reload_pos_data(),
            ),
            Mapping(
                Key.Minus,
                "Decrease mesh typology  scale",
                lambda: self._z_scale.scale(1 / __scale_factor)
                and self._reload_pos_data(),
            ),
            ModalControl(
                "g",
                [
                    DummyMappingLine(
                        lambda: f"grid indexing every: {int(self.grid_every)}"
                    ),
                    Mapping(
                        Key.Plus,
                        "Increase mesh density",
                        lambda: self.grid_every.increment()
                        and self._reload_pos_data(update_grid=True),
                    ),
                    Mapping(
                        Key.Minus,
                        "Decrease mesh density",
                        lambda: self.grid_every.decrement()
                        and self._reload_pos_data(update_grid=True),
                    ),
                ],
                "grid density",
            ),
        ]

    def _reload_pos_data(self, update_grid=False):
        every = int(self.grid_every)
        data = dict(zs=self.z_data_[::every, ::every] * float(self._z_scale))
        cmap = get_colormap("jet")

        if update_grid:
            data.update(
                dict(
                    xs=self.grid[0][::every, ::every],
                    ys=self.grid[1][::every, ::every],
                    colors=cmap.map(map_array_to_0_1(data["zs"])).reshape(
                        *data["zs"].shape, 4
                    ),
                )
            )
        self.mesh_visual.set_data(**data)

    def construct_plugin(
        self,
        **kwargs,
    ) -> bool:
        nums = self.grid[0].shape[0] * self.grid[0].shape[0]
        if nums > 1_000_000:
            self.grid_every.set(int(nums // 1_000_000))

        self.mesh_visual = FixedGridMesh(
            DUMMY_AXIS_VAL,
            DUMMY_AXIS_VAL,
            DUMMY_AXIS_VAL,
            shading="smooth",
            parent=self.visualiser.view.scene,
            # antialias=float(self._antialias),
        )
        self._reload_pos_data(update_grid=True)
        if not self.had_set_range:
            self.set_range()
        return True

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        self.mesh_visual.visible = True
        self._reload_pos_data()
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        self.mesh_visual.visible = False
        return True


class VisualisableDisplacementMap(ToggleableMixin, VisualisablePoints):
    def __init__(self, image_path: str):
        self._z_scale = ScalableFloat(0.3, upper_bound=10)
        if image_path is not None:
            with Image.open(image_path) as im:
                self.z_data = np.array(im.convert("L"))
                self.z_data_ = self.z_data
        self.grid = np.indices(self.z_data.shape)
        self.z_data = self.z_data.ravel()
        point_data = np.vstack(
            [
                self.grid[0].ravel(),
                self.grid[1].ravel(),
                self.z_data * float(self._z_scale),
            ],
        ).T

        super(VisualisableDisplacementMap, self).__init__(point_data)

        __scale_factor = 1.25
        self.keys[:0] = [
            DummyMappingLine(lambda: f"dis scale: {float(self._z_scale):.2f}"),
            Mapping(
                Key.Plus,
                "Increase points typology scale",
                lambda: self._z_scale.scale(__scale_factor)
                and self._reload_pos_data(self._compute_new_point_data()),
            ),
            Mapping(
                Key.Minus,
                "Decrease points typology  scale",
                lambda: self._z_scale.scale(1 / __scale_factor)
                and self._reload_pos_data(self._compute_new_point_data()),
            ),
        ]

    def _compute_new_point_data(self):
        self.point_data[:, 2] = self.z_data * float(self._z_scale)
        return self.point_data

    def turn_on_plugin(self):
        if not super().turn_on_plugin():
            return False
        self.points_visual.visible = True
        self._reload_pos_data(self._compute_new_point_data())
        return True

    def turn_off_plugin(self):
        if not super().turn_off_plugin():
            return False
        self.points_visual.visible = False
        return True

    def construct_plugin(
        self,
        **kwargs,
    ) -> bool:
        cmap = get_colormap("jet")
        colours = cmap.map(map_array_to_0_1(self.z_data))
        super().construct_plugin(face_color=colours, **kwargs)
        self.set_antialias(0.05)

        return True


class VisualisableDisplacementMapLoopWithGlob(
    IntervalUpdatableMixin, VisualisableDisplacementMap
):
    """A version that loop through all matched files"""

    def __init__(self, image_glob_path: str):
        self.globbed_images = sorted(glob.glob(image_glob_path))
        self.current_image_path = None
        if len(self.globbed_images) < 1:
            raise ValueError(
                f"No images found with the glob string '{image_glob_path}'"
            )

        def iterator():
            while True:
                yield from self.globbed_images

        self.iterator = iterator()
        # initialise with the first image
        super().__init__(image_path=self.__get_next_image())

        # line to display current image
        self.keys[:0] = [
            DummyMappingLine(
                lambda: f"Displaying: {self.current_image_path.split('/')[-1]}\n"
            ),
        ]

    def __get_next_image(self):
        self.current_image_path = next(self.iterator)
        return self.current_image_path

    def on_update(self) -> None:
        super().on_update()
        image_path = self.__get_next_image()
        with Image.open(image_path) as im:
            self.z_data = np.array(im.convert("L")).ravel()
        cmap = get_colormap("jet")
        colours = cmap.map(map_array_to_0_1(self.z_data))
        self.points_visual.set_data(face_color="white")
        self._reload_pos_data(self._compute_new_point_data())
        self.points_visual.update_data_color(colours)

        # update status
        self.other_plugins.VisualisableStatusBar.update_status()


class AlternativeVisTrigger(TriggerableMixin, VisualisablePlugin):
    def __init__(self):
        super().__init__()
        self.keys = [Mapping("t", "toggle", self.__toggle)]

    def construct_plugin(self):
        # sync the scale
        self.other_plugins.VisualisableMesh._z_scale = (
            self.other_plugins.VisualisableDisplacementMap._z_scale
        )

        self.other_plugins.VisualisableMesh.turn_off_plugin()
        try:
            self.other_plugins.VisualisableDisplacementMap.turn_on_plugin()
        except Exception as e:
            print(e)

    def __toggle(self):
        self.other_plugins.VisualisableMesh.toggle()
        self.other_plugins.VisualisableDisplacementMap.toggle()


def run():
    args = DisplacementMapArgParser(underscores_to_dashes=True).parse_args()

    visualiser = Visualiser(
        title="Displacement Map Visualiser",
    )
    visualiser.register_plugin(VisualisableStatusBar())
    if args.glob:
        displacement_plugin_cls = VisualisableDisplacementMapLoopWithGlob
    else:
        displacement_plugin_cls = VisualisableDisplacementMap
        visualiser.register_plugin(VisualisableMesh(args.image_path))
        visualiser.register_plugin(
            AlternativeVisTrigger(),
            depends_on={"VisualisableMesh", "VisualisableDisplacementMap"},
        )

    visualiser.register_plugin(displacement_plugin_cls(args.image_path))
    visualiser.initialise()

    visualiser.run(regular_update_interval=1)


if __name__ == "__main__":
    run()
