from collections import defaultdict
from typing import List, Union

import numpy as np
from loguru import logger
from vispy.scene import LinePlot

from easy_visualiser.plugin_capability import ZoomableMixin
from easy_visualiser.plugins import VisualisablePlugin


class Visualisable3DLine(ZoomableMixin, VisualisablePlugin):
    def __init__(self):
        super().__init__()

        self.line_plots = defaultdict(
            lambda: LinePlot(
                color="white",
                parent=self.visualiser.visual_parent,
            )
        )

    def plot(self, name: str, data: Union[np.ndarray, List], **kwargs):
        if isinstance(data, np.ndarray):
            pos = data
        elif isinstance(data, list) and (
            len(data) > 0 and isinstance(data[0], np.ndarray)
        ):
            """This is a list of ndarray"""
            pos = np.array(data)
            # "TRY" to infer dimensions and re-arrange if needed
            if len(pos.shape) == 3:
                if pos.shape[2] == 1:
                    pos = pos[..., 0]
            if len(pos.shape) == 2:
                if pos.shape[1] != 3 and pos.shape[0] == 3:
                    pos = pos.swapaxes(0, 1)
        else:
            logger.error(f"Unrecognised data type {type(data)} for {data}")
            return
            # raise ValueError
        self.line_plots[name].set_data(data=pos, **kwargs)
