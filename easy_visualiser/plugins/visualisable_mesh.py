import numpy as np
from PIL import Image
from vispy.color import get_colormap

from easy_visualiser.key_mapping import Key, Mapping, MappingOnlyDisplayText
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.plugin_capability import ToggleableMixin, TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import IncrementableInt, ScalableFloat, map_array_to_0_1
from easy_visualiser.utils.dummy import DUMMY_AXIS_VAL
from easy_visualiser.visuals.gridmesh import FixedGridMesh


class VisualisableMesh(ToggleableMixin, TriggerableMixin, VisualisablePlugin):
    def __init__(self, image_path: str):
        super().__init__()
        self._marker_scale = ScalableFloat(1, upper_bound=50)
        self._antialias = ScalableFloat(0.25, upper_bound=10)

        self.add_mapping(
            Mapping("z", "reset zoom", lambda: self.set_range()),
        )
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

        self.add_mappings(
            MappingOnlyDisplayText(lambda: f"scale: {float(self._z_scale):.2f}"),
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
                    MappingOnlyDisplayText(
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
            front=True,
        )

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
            parent=self.visualiser.visual_parent,
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
