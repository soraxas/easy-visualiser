import os
from typing import Tuple, Optional, Dict, Callable

import numpy as np
from scipy.interpolate import griddata, NearestNDInterpolator
from vispy.color import get_colormap
from vispy.scene import XYZAxis

from plannerGraphVisualiser.abstract_visualisable_plugin import (
    VisualisablePlugin, UpdatableMixin,
)
from plannerGraphVisualiser.dummy import DUMMY_AXIS_VAL
from plannerGraphVisualiser.gridmesh import FixedGridMesh


class VisualisablePrincipleAxis(UpdatableMixin,VisualisablePlugin):
    bathy_mesh = None
    bathy_intert: NearestNDInterpolator = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return "principle_axis"

    @property
    def target_file(self) -> str:
        return self.args.depth_datapath

    def construct_plugin(self) -> None:
        super().construct_plugin()

        self.axis_visual = XYZAxis(
            parent=self.args.view.scene,
            width=5,
        )

    def on_update(self) -> None:
        _pos = np.array(
            [[0, 0, 0], [1, 0, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 1]],
            dtype=np.float,
        )

        _pos *= self.args.principle_axis_length
        if self.other_plugins_mapper['bathymetry'].last_min_pos is not None:
            _pos += self.other_plugins_mapper['bathymetry'].last_min_pos

        _pos[:, 2] -= self.args.principle_axis_z_offset

        self.axis_visual.set_data(pos=_pos)

