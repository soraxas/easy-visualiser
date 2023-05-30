from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from vispy import scene
from vispy.plot import PlotWidget

from easy_visualiser.modded_components import PlotWidgetWithSyncedCamera
from easy_visualiser.plugin_capability import WidgetOption, WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import infer_bounds


class VisualisableLinePlot(WidgetsMixin, VisualisablePlugin):
    pw: PlotWidget

    def __init__(
        self,
        bounds: Optional[Dict] = None,
        widget_option: WidgetOption = None,
        name: str = "my_plot",
        custom_camera=None,
        lineplot_kwargs=None,
    ):
        super().__init__(name=name)
        if lineplot_kwargs is None:
            lineplot_kwargs = dict(width=2, marker_size=5, title=self.name)
        self.lineplot_kwargs = lineplot_kwargs

        self.bounds = bounds
        if widget_option is None:
            widget_option = WidgetOption()
        self.widget_option = widget_option
        self.plots: List[scene.LinePlot] = []
        self.custom_camera = custom_camera

    def get_plot(self, idx) -> scene.LinePlot:
        while idx >= len(self.plots):
            self.plots.append(self.pw.plot(([0], [0]), **self.lineplot_kwargs))
        return self.plots[idx]

    def plot(
        self,
        data: Union[np.ndarray, Tuple[List, List]],
        idx: int = 0,
        auto_range: bool = False,
        **kwargs
    ):
        self.get_plot(idx=idx).set_data(data=data, **kwargs)
        if auto_range:
            self.enforce_bounds(infer_bounds(data))

    def enforce_bounds(self, bounds: Dict = None):
        # bounds is like {'x': [min, max], 'y': [min, max]}
        if bounds is None:
            bounds = self.bounds
        if bounds is not None:
            self.pw.camera.set_range(**bounds, margin=0)

    def get_constructed_widgets(self):
        if self.custom_camera is not None:
            self.pw = PlotWidgetWithSyncedCamera(
                custom_camera=self.custom_camera,
                fg_color="w",
            )
            #################################
            # self.enforce_bounds()
        else:
            self.pw = PlotWidget(
                fg_color="w",
            )
        return [(self.pw, self.widget_option)]
