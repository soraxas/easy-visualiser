import numpy as np
from vispy.scene import XYZAxis

from plannerGraphVisualiser.easy_visualiser.abstract_visualisable_plugin import (
    VisualisablePlugin,
    UpdatableMixin,
)


class VisualisablePrincipleAxis(UpdatableMixin, VisualisablePlugin):
    axis_visual: XYZAxis
    __axis_pos = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1]],
        dtype=np.float,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return "principle_axis"

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.axis_visual = XYZAxis(
            parent=self.args.view.scene,
            width=5,
        )

    def on_update(self) -> None:
        pass
        self.__axis_pos *= self.args.principle_axis_length
        if self.other_plugins_mapper["bathymetry"].last_min_pos is not None:
            self.__axis_pos += self.other_plugins_mapper["bathymetry"].last_min_pos

        self.__axis_pos[:, 2] -= self.args.principle_axis_z_offset

        self.axis_visual.set_data(pos=self.__axis_pos)
