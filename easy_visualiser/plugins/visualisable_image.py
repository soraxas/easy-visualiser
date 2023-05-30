import numpy as np
from vispy import scene

from easy_visualiser.key_mapping import Mapping
from easy_visualiser.modded_components import LockedPanZoomCamera
from easy_visualiser.plugin_capability import TriggerableMixin, WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import boolean_to_onoff


class VisualisableImage(WidgetsMixin, VisualisablePlugin):
    texture_format = "auto"  # None for CPUScaled, "auto" for GPUScaled

    def __init__(
        self,
        image_array: np.array,
        widget_configs=None,
        image_kwargs=None,
    ):
        super().__init__()
        if widget_configs is None:
            widget_configs = dict(col=0, row=0, col_span=2)
        self.image_array = image_array
        self.widget_configs = widget_configs

        if image_kwargs is None:
            image_kwargs = dict(
                cmap="jet",
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=self.texture_format,
                # parent=view.scene,
            )
        self.image_kwargs = image_kwargs

    @property
    def name(self):
        return "image"

    def get_constructed_widgets(self):
        grid = scene.Grid()
        grid.add_view().add(scene.Image(self.image_array, **self.image_kwargs))
        return grid, self.widget_configs
