import numpy as np
from PIL import Image
from vispy.color import get_colormap

from easy_visualiser.key_mapping import Key, Mapping, MappingOnlyDisplayText
from easy_visualiser.plugin_capability import ToggleableMixin
from easy_visualiser.plugins import VisualisablePoints
from easy_visualiser.utils import ScalableFloat, map_array_to_0_1


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
        self.add_mappings(
            MappingOnlyDisplayText(lambda: f"dis scale: {float(self._z_scale):.2f}"),
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
            front=True,
        )

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
        VisualisablePoints.construct_plugin(self, face_color=colours, **kwargs)
        self.set_antialias(0.05)

        return True
