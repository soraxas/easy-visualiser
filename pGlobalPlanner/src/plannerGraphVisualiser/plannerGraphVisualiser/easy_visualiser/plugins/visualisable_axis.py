import numpy as np
from vispy.scene import XYZAxis

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)

axis_pos_template = np.array(
    [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1]],
    dtype=np.float,
)


class VisualisablePrincipleAxis(VisualisablePlugin):
    axis_visual: XYZAxis
    _axis_pos = None

    def __init__(
        self,
        *args,
        axis_length: float = 1,
        origin: np.array = np.array([0, 0, 0], dtype=np.float)
    ):
        super().__init__(*args)
        self.axis_length = axis_length
        self._set_origin(origin, update_display=False)

    def _set_origin(self, origin, update_display: bool = True):
        assert len(origin) == 3
        self._axis_pos = (axis_pos_template.copy() * self.axis_length) + origin
        if update_display:
            self.axis_visual.set_data(pos=self._axis_pos)

    @property
    def name(self):
        return "principle_axis"

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.axis_visual = XYZAxis(
            parent=self.args.view.scene,
            width=5,
        )
        self.axis_visual.set_data(pos=self._axis_pos)