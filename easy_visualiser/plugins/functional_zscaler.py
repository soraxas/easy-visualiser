from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
)

from plannerGraphVisualiser.easy_visualiser.utils import AxisScaler


class AxisScalerPlugin(VisualisablePlugin):
    def __init__(self, z_scale_factor: float, name: str = "axis_scaler"):
        super().__init__(name=name)
        self.scaler = AxisScaler(scale_factor=z_scale_factor)
