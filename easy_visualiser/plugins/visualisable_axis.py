import numpy as np
from vispy.scene import XYZAxis

from easy_visualiser.plugins import VisualisablePlugin

axis_pos_template = np.array(
    [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1]],
    dtype=np.float16,
)


class VisualisablePrincipleAxis(VisualisablePlugin):
    axis_visual: XYZAxis
    _axis_pos = None

    def __init__(
        self,
        axis_length: float = 1,
        origin: np.ndarray = np.array([0, 0, 0], dtype=np.float16),
    ):
        super().__init__()
        self.axis_length = axis_length
        self._set_origin(origin, update_display=False)

    def _set_origin(self, origin, update_display: bool = True):
        assert len(origin) == 3
        self._axis_pos = (axis_pos_template.copy() * self.axis_length) + origin
        if update_display:
            self.axis_visual.set_data(pos=self._axis_pos)

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.axis_visual = XYZAxis(
            parent=self.visualiser.visual_parent,
            width=5,
        )
        self.axis_visual.set_data(pos=self._axis_pos)
