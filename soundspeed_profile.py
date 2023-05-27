import os
from typing import List

import numpy as np
from icecream import ic
from tap import Tap
from vispy import app, scene
from vispy.plot import PlotWidget

from easy_visualiser.plugin_capability import (
    TriggerableMixin,
    WidgetOption,
    WidgetsMixin,
)
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.plugins.visualisable_status_bar import VisualisableStatusBar

from .easy_visualiser.modal_control import ModalControl
from .easy_visualiser.modded_components import (
    LockedPanZoomCamera,
    PlotWidgetWithSyncedCamera,
    SyncedPanZoomCamera,
)
from .easy_visualiser.utils import boolean_to_onoff

os.putenv("NO_AT_BRIDGE", "1")

import netCDF4

from .easy_visualiser.visualiser import Visualiser


class Plottable:
    def __init__(self, dataset: netCDF4.Dataset, variable: str):
        self.dataset = dataset
        self.variable = variable

    def _get_var(self, var: str) -> netCDF4.Variable:
        return self.dataset.variables[var]

    def get_array(
        self,
        var: str,
        filter_valid: bool = False,
        filter_missing: bool = False,
        fill_value=0,
        force_using_timestep=None,
    ):
        variable = self._get_var(var)
        _var = variable
        if force_using_timestep is not None:
            _var = variable[force_using_timestep : force_using_timestep + 1, ...]
        array = np.array(_var).astype(np.float32)
        if filter_valid:
            valid_range = variable.valid_range
            array[(array < valid_range[0]) | (array > valid_range[1])] = fill_value
        if filter_missing:
            missing_value = variable.missing_value
            array[array == missing_value] = fill_value
        return array

    def get_coordinates(self, coordinates: str) -> List[np.ndarray]:
        return [self.get_array(var) for var in coordinates.split(" ")]

    def get_coordinates_array_of_var(self, var: str) -> List[np.ndarray]:
        return self.get_coordinates(self.get_coordinates_of_var(var))

    def get_coordinates_of_var(self, var: str) -> str:
        return self._get_var(var).coordinates


def _filter_out(x, y):
    _needed = x > 0
    return x[_needed], y[_needed]


class VisualisableImage(WidgetsMixin, TriggerableMixin, VisualisablePlugin):
    def __init__(self, botz: np.array):
        super().__init__()
        self.botz = botz
        self.keys = [
            (
                "a",
                lambda: f"toggle auto-update [{boolean_to_onoff(self.auto_update)}]",
                self.__toggle_auto_update,
            ),
            (
                "r",
                lambda: f"toggle auto-resize [{boolean_to_onoff(self.auto_resize)}]",
                self.__toggle_auto_resize,
            ),
        ]
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
        grid = scene.Grid()
        vb = grid.add_view(col=0, col_span=5)

        vb.camera = LockedPanZoomCamera()
        vb.camera.aspect = 1
        vb.camera.rect = [0, 0, self.botz.shape[1], self.botz.shape[0]]
        vb.add(
            scene.Image(
                self.botz,
                cmap="jet",
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=texture_format,
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

        @self.visualiser.canvas.events.mouse_move.connect
        def on_move(ev):
            if not self.auto_update:
                return
            pos = vb.camera.transform.imap(ev.pos)
            i = int(pos[0] // scale)
            j = int(pos[1] // scale)
            # ic(pos, ev.pos)
            if 0 <= i < sound_speed.shape[0] and 0 <= j < sound_speed.shape[1]:
                # ic(i, j, botz.shape, sound_speed.shape)
                dd = _filter_out(sound_speed[i, j, :], plottable.get_array("zc"))
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
        vb2.camera.rect = [0, 0, self.botz.shape[1], self.botz.shape[0]]
        _botz = self.botz.copy()
        _botz[_botz < 0] = -1

        vb2.add(
            scene.Image(
                _botz,
                cmap="jet",
                # clim=clim,
                # fg_color=(0.5, 0.5, 0.5, 1),
                texture_format=texture_format,
            )
        )
        return grid, dict(col=0, row=0, col_span=2)


class VisualisableLinePlot(WidgetsMixin, VisualisablePlugin):
    pw: PlotWidget

    def __init__(
        self,
        bounds,
        widget_option: WidgetOption = None,
        name="plot",
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

    def plot(self, data, idx=0, **kwargs):
        self.get_plot(idx=idx).set_data(data=data, **kwargs)

    def enforce_bounds(self):
        self.pw.camera.set_range(x=self.bounds["x"], y=self.bounds["y"], margin=0)

    def get_constructed_widgets(self):
        if self.custom_camera is None:
            self.pw = PlotWidget(
                fg_color="w",
            )
        else:
            self.pw = PlotWidgetWithSyncedCamera(
                custom_camera=self.custom_camera,
                fg_color="w",
            )
            #################################
            # self.enforce_bounds()
        return [(self.pw, self.widget_option)]


class VisualisableVolumePlot(WidgetsMixin, VisualisablePlugin):
    def __init__(self, volume_data: np.array):
        super().__init__()
        self.volume_data = volume_data

    @property
    def name(self):
        return "volume plot"

    def get_constructed_widgets(self):
        view = scene.ViewBox()
        view.camera.aspect = 1
        view.add(
            scene.Volume(
                self.volume_data,
                # clim=clim,
                texture_format=texture_format,
            )
        )
        view.camera = "turntable"
        return [(view, dict(col=0, row=1, col_span=2))]


from skimage.transform import resize

if __name__ == "__main__":
    ##################################################
    # gather data
    class SoundSpeedProfileArgParser(Tap):
        netcdf_path: str

        def configure(self):
            self.add_argument(
                "netcdf_path",
                metavar="NETCDF",
                type=str,
                nargs="?",
                default="/home/tin/work/dataset/9308_out_cf-396MB-WAXA.nc",
            )

    args = SoundSpeedProfileArgParser().parse_args()

    dataset = netCDF4.Dataset(
        args.netcdf_path,
    )
    # dataset = netCDF4.Dataset("/home/tin/work/dataset/lombok_out_cf.nc")
    texture_format = "auto"  # None for CPUScaled, "auto" for GPUScaled

    plottable = Plottable(dataset, "sound")

    sound_speed = plottable.get_array(
        "sound",
        filter_valid=True,
        force_using_timestep=1,
        # fill_value=plottable.get_array("sound").min()
        fill_value=np.nan,
        # fill_value=1000
    )
    sound_speed = sound_speed[0, ...]
    sound_speed = np.moveaxis(sound_speed, 0, -1)

    scale = 2
    botz = plottable.get_array("botz", filter_missing=True)
    botz = np.rollaxis(botz, 1)
    botz = -botz
    botz = resize(botz, (botz.shape[0] * scale, botz.shape[1] * scale))

    zc = plottable.get_array("zc")
    zc_bounds = [zc.min(), 100]

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
        VisualisableLinePlot(
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
        VisualisableLinePlot(
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
        VisualisableLinePlot(
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
    visualiser.register_plugin(VisualisableImage(botz))
    #############################################
    visualiser.initialise()
    app.run()
