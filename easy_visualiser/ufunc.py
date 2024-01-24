from abc import ABC
from typing import TYPE_CHECKING

from vispy import scene

from easy_visualiser.key_mapping import Key, Mapping
from easy_visualiser.plugins import VisualisablePoints
from easy_visualiser.utils import ToggleableBool

from .plugin_capability import ToggleableMixin, TriggerableMixin
from .plugins import VisualisablePlugin

if TYPE_CHECKING:
    from .visualiser import Visualiser

import numpy as np


def ensure_nparray(x):
    if not isinstance(x, np.ndarray):
        x = np.asarray(x)
    if len(x.shape) > 3:
        x = x.reshape(-1, *x.shape[-2:])
    return x


import warnings
from functools import wraps

import numpy as np

from easy_visualiser.key_mapping import Key, Mapping, MappingOnlyDisplayText
from easy_visualiser.modal_control import ModalControl
from easy_visualiser.modded_components import MarkerWithModifiablePos
from easy_visualiser.plugin_capability import TriggerableMixin
from easy_visualiser.plugins import VisualisablePlugin
from easy_visualiser.utils import ScalableFloat
from easy_visualiser.utils.dummy import DUMMY_POINTS


def visualiser_non_closing_guard(func):
    @wraps(func)
    def call_func(visualiser: "Visualiser", *args):
        if not bool(visualiser):
            # visualiser is closing. Do nothing
            warnings.warn(
                f"Ignoring 'visualiser.{func.__name__}(...)' as Visualiser is closing.",
                RuntimeWarning,
            )
            return
        return func(visualiser, *args)

    return call_func


class VisualisableLine(TriggerableMixin, VisualisablePlugin):
    """
    Visualise 3D lines
    """

    lines_visual: scene.Line

    def __init__(self, points: np.ndarray = np.zeros([0, 3]), **kwargs):
        super().__init__(**kwargs)
        self._marker_scale = ScalableFloat(1, upper_bound=50)
        self._antialias = ScalableFloat(0.25, upper_bound=10)
        self._cached_plotting_kwargs = dict()

        # self.add_mappings(
        #     ModalControl(
        #         "m",
        #         [
        #             MappingOnlyDisplayText(
        #                 lambda: f"marker size: {float(self._marker_scale):.2f}"
        #             ),
        #             Mapping(
        #                 Key.Plus,
        #                 "Increase marker size",
        #                 lambda: self._marker_scale.scale(1.25)
        #                 and self.lines_visual.update_data(
        #                     size=float(self._marker_scale)
        #                 ),
        #             ),
        #             Mapping(
        #                 Key.Minus,
        #                 "Decrease marker size",
        #                 lambda: self._marker_scale.scale(1 / 1.25)
        #                 and self.lines_visual.update_data(
        #                     size=float(self._marker_scale)
        #                 ),
        #             ),
        #         ],
        #         "Marker",
        #     ),
        #     ModalControl(
        #         "a",
        #         [
        #             MappingOnlyDisplayText(
        #                 lambda: f"antialias: {float(self._antialias):.4f}"
        #             ),
        #             Mapping(
        #                 Key.Plus,
        #                 "Increase antialias",
        #                 lambda: self._antialias.scale(1.25)
        #                 and self.set_antialias(self._antialias),
        #             ),
        #             Mapping(
        #                 Key.Minus,
        #                 "Decrease antialias",
        #                 lambda: self._antialias.scale(1 / 1.25)
        #                 and self.set_antialias(self._antialias),
        #             ),
        #         ],
        #         "Anti-alias",
        #     ),
        #     Mapping("z", "reset zoom", lambda: self.set_range()),
        # )
        self.point_data = points

    def construct_plugin(
        self,
        **kwargs,
    ) -> bool:
        super().construct_plugin()
        self.lines_visual = scene.Line(
            parent=self.visualiser.visual_parent,
            # antialias=float(self._antialias),
        )
        # self._antialias.set(self.lines_visual.antialias)
        # self.visualiser.grid.add_widget(col=4, row=4)

        # default_kwargs = dict(
        #     edge_width=0,
        #     face_color="w",
        #     size=1,
        #     symbol="o",
        # )
        # default_kwargs.update(kwargs)

        self.set_line(self.point_data)
        return True

    def set_line(self, pos: np.ndarray, *args, **kwargs):
        assert len(pos.shape) == 2
        if pos.shape[0] <= 0:
            return

        kwargs["pos"] = pos
        self.lines_visual.set_data(*args, **kwargs)
        self._cached_plotting_kwargs = dict(kwargs)

        if not self.had_set_range:
            self.set_range()


class _SpinUntlKeyPress_Helper(ToggleableMixin, VisualisablePlugin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # this represent if the monitoring key has been pressed
        self.pressed = ToggleableBool(False)
        # main callback
        self.add_mapping(
            Mapping(
                Key(["Space"]),
                "[Continue Processing]",
                lambda: self.pressed.set(True),
            )
        )

    def turn_off_plugin(self) -> bool:
        if not super().turn_off_plugin():
            return False

        self.visualiser.hooks.on_visualiser_close.remove_hook(identifier=self)
        return True

    def turn_on_plugin(self) -> bool:
        if not super().turn_on_plugin():
            return False

        self.pressed.set(False)  # reset
        # monitor the visualiser close event, to auto-set the toggleable bool
        self.visualiser.hooks.on_visualiser_close.add_hook(
            lambda: self.pressed.set(True), identifier=self
        )
        return True


class PlottingUFuncMixin(ABC):
    def spin_once(self):
        self.app.sleep(0.05)
        self.app.process_events()

    @visualiser_non_closing_guard
    def spin_until_keypress(self: "Visualiser"):
        # _pressed = ToggleableBool(False)

        with self.get_existing_or_construct(
            plugin_type=_SpinUntlKeyPress_Helper
        ) as plug:
            while not plug.pressed:
                self.spin_once()

    def scatter(self: "Visualiser", pos, *args, name: str = None, **kwargs):
        """
        Scatter plots.
        """
        pos = ensure_nparray(pos)

        self.get_existing_or_construct(
            plugin_type=VisualisablePoints,
            name=name,
        ).set_points(pos=pos, *args, **kwargs)

    def plot(
        self: "Visualiser",
        pos,
        *args,
        name: str = None,
        connect: str = "strip",
        width: int = 5,
        color: str = "red",
        **kwargs,
    ):
        pos = ensure_nparray(pos)

        kwargs.update(
            dict(
                connect=connect,
                width=width,
                color=color,
            )
        )

        self.get_existing_or_construct(
            plugin_type=VisualisableLine,
            name=name,
        ).set_line(pos=pos, *args, **kwargs)

    def imshow(
        self: "Visualiser",
        image,
        *args,
        name: str = None,
        connect: str = "strip",
        width: int = 5,
        color: str = "red",
        **kwargs,
    ):
        image = ensure_nparray(image)

        # kwargs.update(
        #     dict(
        #     widget_configs=dict(col=0, row=0, col_span=5, row_span=2),
        #     )
        # )

        from .plugins import VisualisableImage

        _plug = self.get_existing_or_construct(
            # image,
            plugin_type=VisualisableImage,
            name=name,
            #
            panzoom_lock=False,
        )

        _plug.set_image(image, *args, **kwargs)
