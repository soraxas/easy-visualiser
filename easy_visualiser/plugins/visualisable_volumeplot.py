import numpy as np
from vispy import scene

from easy_visualiser.plugin_capability import WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin


class VisualisableVolumePlot(WidgetsMixin, VisualisablePlugin):
    texture_format = "auto"

    def __init__(self, volume_data: np.array):
        super().__init__()
        self.volume_data = volume_data

    @property
    def name(self):
        return "volume_plot"

    def get_constructed_widgets(self):
        view = scene.ViewBox()
        view.camera.aspect = 1
        view.add(
            scene.Volume(
                self.volume_data,
                # clim=clim,
                texture_format=self.texture_format,
            )
        )
        view.camera = "turntable"
        return [(view, dict(col=0, row=1, col_span=2))]
