import os
import pickle

import numpy as np
from tap import Tap
from vispy import scene

from easy_visualiser.key_mapping import Mapping
from easy_visualiser.modded_components import LockedPanZoomCamera, SyncedPanZoomCamera
from easy_visualiser.plugin_capability import TriggerableMixin, WidgetOption
from easy_visualiser.plugins import (
    Visualisable2DLinePlot,
    VisualisableImage,
    VisualisableStatusBar,
    VisualisableVolumePlot,
)
from easy_visualiser.utils import boolean_to_onoff
from easy_visualiser.utils.netcdf import PlottableNetCDF4
from easy_visualiser.visualiser import Visualiser

os.putenv("NO_AT_BRIDGE", "1")


def _filter_out(x, y):
    _needed = x > 0
    return x[_needed], y[_needed]


class VisualisableImageSynced(VisualisableImage, TriggerableMixin):
    def __init__(self, image_array: np.array):
        super().__init__(image_array, widget_configs=dict(col=0, row=0, col_span=2))
        self.add_mappings(
            Mapping(
                "a",
                lambda: f"toggle auto-update [{boolean_to_onoff(self.auto_update)}]",
                self.__toggle_auto_update,
            ),
            Mapping(
                "r",
                lambda: f"toggle auto-resize [{boolean_to_onoff(self.auto_resize)}]",
                self.__toggle_auto_resize,
            ),
        )
        self.auto_update = True
        self.auto_resize = True

    def __toggle_auto_update(self):
        self.auto_update = not self.auto_update

    def __toggle_auto_resize(self):
        self.auto_resize = not self.auto_resize

    @property
    def name(self):
        return "image"

    def get_constructed_widgets(self):
        # grid, widget_configs = super().get_constructed_widgets()
        grid = scene.Grid()
        vb = grid.add_view(col=0, col_span=5)

        vb.camera = LockedPanZoomCamera()
        vb.camera.aspect = 1
        vb.camera.rect = [0, 0, self.image_array.shape[1], self.image_array.shape[0]]
        vb.add(
            scene.Image(
                self.image_array,
                cmap="jet",
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=self.texture_format,
                # parent=view.scene,
            )
        )

        self.other_plugins.plot_raw.plots.append(
            self.other_plugins.plot_raw.pw.plot(
                data=([0], [0]),
                edge_width=0,
                title="netcdf",
            )
        )
        self.other_plugins.plot_raw.plots.append(
            self.other_plugins.plot_raw.pw.plot(
                data=([0], [0]),
                edge_width=5,
                marker_size=0,
                title="spline",
            )
        )
        scale = 2

        @self.visualiser.canvas.events.mouse_move.connect
        def on_move(ev):
            if not self.auto_update:
                return
            pos = vb.camera.transform.imap(ev.pos)
            i = int(pos[0] // scale)
            j = int(pos[1] // scale)
            # ic(pos, ev.pos)
            if 0 <= i < sound_speed.shape[0] and 0 <= j < sound_speed.shape[1]:
                # ic(i, j, image_array.shape, sound_speed.shape)
                dd = _filter_out(sound_speed[i, j, :], zc)
                if len(dd[0]) <= 0:
                    dd = np.array(([0, 0.01], [0, 0.01]))

                z = np.arange(dd[1].min(), dd[1].max(), step=1)
                self.other_plugins.plot_raw.plot(dd, color=(0, 0, 0, 1))

                if self.auto_resize:
                    self.other_plugins.plot_raw.enforce_bounds()

                ###################################
                from scipy.interpolate import CubicSpline

                cubic_spline = CubicSpline(dd[1], dd[0])

                self.other_plugins.plot_raw.plot(
                    (cubic_spline(z), z),
                    color="r",
                    width=4,
                    idx=1,
                )
                zp = cubic_spline.derivative(1)(z)
                self.other_plugins.plot_spline_p.plot(
                    (zp, z),
                )
                if self.auto_resize:
                    self.other_plugins.plot_spline_p.pw.camera.set_range(
                        x=[zp.min() - 0.05, zp.max() + 0.05], y=zc_bounds, margin=0
                    )
                zpp = cubic_spline.derivative(2)(z)
                self.other_plugins.plot_spline_p_p.plot(
                    (zpp, z),
                )
                if self.auto_resize:
                    self.other_plugins.plot_spline_p_p.pw.camera.set_range(
                        # x=[zpp.min() - 1e-8, zpp.max() + 1e-8],
                        y=zc_bounds,
                        margin=0,
                    )

        vb2 = grid.add_view(col=5)
        vb2.camera = LockedPanZoomCamera()
        vb2.camera.aspect = 1
        vb2.camera.rect = [0, 0, self.image_array.shape[1], self.image_array.shape[0]]

        vb2.add(
            scene.Image(
                self.image_array,
                cmap="jet",
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=self.texture_format,
            )
        )
        return grid, dict(col=0, row=0, col_span=2)


if __name__ == "__main__":
    ##################################################
    # gather data
    class SoundSpeedProfileArgParser(Tap):
        data_path: str

        def configure(self):
            self.add_argument(
                "data_path",
                metavar="PKL",
                type=str,
                nargs="?",
                default="waxa-ocean-soundspeed.pkl",
            )

    args = SoundSpeedProfileArgParser().parse_args()

    with open(args.data_path, "rb") as f:
        data = pickle.load(f)

    sound_speed = data["sound_speed"]
    botz = data["botz"]
    zc = data["zc"]
    zc_bounds = [zc.min(), zc.max() + 100]

    #############################################

    visualiser = Visualiser("netcdf sound speed profile viewer")
    visualiser.register_plugin(
        VisualisableVolumePlot(np.flipud(np.rollaxis(sound_speed, 1)))
    )
    visualiser.register_plugin(
        VisualisableStatusBar(
            widget_option=WidgetOption(
                row=1,
                col=1,
            )
        )
    )
    visualiser.register_plugin(
        Visualisable2DLinePlot(
            bounds=dict(
                x=[np.nanmin(sound_speed), np.nanmax(sound_speed)],
                y=zc_bounds,
            ),
            widget_option=WidgetOption(col=2, row=0, row_span=2, col_span=2),
            name="plot_raw",
            custom_camera=SyncedPanZoomCamera(
                "depthplot", sync_xaxis=False, sync_yaxis=True
            ),
        )
    )
    visualiser.register_plugin(
        Visualisable2DLinePlot(
            bounds=dict(
                x=[np.nanmin(sound_speed), np.nanmax(sound_speed)],
                y=zc_bounds,
            ),
            widget_option=WidgetOption(col=4, row=0, row_span=2, col_span=2),
            name="plot_spline_p",
            custom_camera=SyncedPanZoomCamera(
                "depthplot", sync_xaxis=False, sync_yaxis=True
            ),
        )
    )
    visualiser.register_plugin(
        Visualisable2DLinePlot(
            bounds=dict(
                x=[np.nanmin(sound_speed), np.nanmax(sound_speed)],
                y=zc_bounds,
            ),
            widget_option=WidgetOption(col=5, row=0, row_span=2, col_span=2),
            name="plot_spline_p_p",
            custom_camera=SyncedPanZoomCamera(
                "depthplot", sync_xaxis=False, sync_yaxis=True
            ),
        )
    )
    # visualiser.register_plugin(VisualisableImage(botz))
    visualiser.register_plugin(VisualisableImageSynced(botz))
    ############################################
    visualiser.initialise()
    visualiser.run()
