import numpy as np
from vispy import scene

from easy_visualiser.key_mapping import Mapping
from easy_visualiser.modded_components import LockedPanZoomCamera
from easy_visualiser.plugin_capability import TriggerableMixin, WidgetsMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import boolean_to_onoff


class VisualisableImage(WidgetsMixin, VisualisablePlugin):
    texture_format = "auto"  # None for CPUScaled, "auto" for GPUScaled

    name: str = "image"

    def __init__(
        self,
        image_array: np.array,
        widget_configs=None,
        image_kwargs=None,
        cmap=None,
        # cmap="jet",
        on_mouse_callback=None,
    ):
        super().__init__()
        if widget_configs is None:
            widget_configs = dict(col=0, row=0, col_span=10)
        self.image_array = image_array
        self.widget_configs = widget_configs

        if image_kwargs is None:
            image_kwargs = dict(
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=self.texture_format,
                # parent=view.scene,
            )
            if cmap:
                image_kwargs["cmap"] = cmap
        self.image_kwargs = image_kwargs
        self.on_mouse_callback = on_mouse_callback

    def get_constructed_widgets(self):
        grid = scene.Grid()
        vb = grid.add_view()
        self.image_visual = scene.Image(self.image_array, **self.image_kwargs)
        self.image_visual.clim = "auto"

        vb.add(self.image_visual)
        vb.camera = LockedPanZoomCamera()
        vb.camera.aspect = 1
        vb.camera.rect = [0, 0, self.image_array.shape[1], self.image_array.shape[0]]
        vb.camera.flip = False, True, False

        tr = vb.get_transform(map_from="canvas", map_to="visual")

        if self.on_mouse_callback is not None:

            @self.visualiser.canvas.events.mouse_move.connect
            def on_move(ev):
                # canvas to visual coordinate
                visual_pos = tr.map(ev.pos)

                # visual to image (zoomed camera view)
                pos = vb.camera.transform.imap(visual_pos)

                if (
                    0 <= pos[1] < self.image_array.shape[0]
                    and 0 <= pos[0] < self.image_array.shape[1]
                ):
                    self.on_mouse_callback(self, pos[:2])

        return grid, self.widget_configs
