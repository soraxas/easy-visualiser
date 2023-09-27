from abc import ABC


from typing import TYPE_CHECKING, List, Type

from easy_visualiser.plugins import VisualisablePoints
from easy_visualiser.key_mapping import Mapping, Key
from easy_visualiser.utils import ToggleableBool

from .plugin_capability import (
    ToggleableMixin,
)
from .plugins import VisualisablePlugin


if TYPE_CHECKING:
    from .visualiser import Visualiser


class PlottingUFuncMixin(ABC):
    def spin_once(self):
        self.app.sleep(0.05)
        self.app.process_events()

    def spin_until_keypress(self: "Visualiser"):
        nativeapp = self.app.native
        # if hasattr(nativeapp, '_in_event_loop') and nativeapp._in_event_loop:
        #     pass  # Already in event loop

        _pressed = ToggleableBool(False)

        class _SpinUntlKeyPress_Helper(ToggleableMixin, VisualisablePlugin):
            keys = [
                Mapping(
                    Key(["Space"]),
                    "[Continue Processing]",
                    lambda: _pressed.set(True),
                )
            ]

        _plug = _SpinUntlKeyPress_Helper()
        self.register_plugin(_plug)

        while not _pressed:
            self.spin_once()

        _plug.turn_off_plugin()
        for _hook in self.hooks.on_keypress_finish:
            _hook()

    def _get_existing_or_default(
        self, plugin_type: Type["VisualisablePlugin"], name: str
    ):
        name = name or f"_default__{plugin_type.__name__}"

        if name not in self.plugins:
            self.register_plugin(plugin_type(), name=name)
        return self.plugins[name]

    def scatter(self: "Visualiser", pos, *args, name: str = None, **kwargs):
        import numpy as np

        def ensure_nparray(x):
            if not isinstance(x, np.ndarray):
                x = np.asarray(x)
            if len(x.shape) > 3:
                x = x.reshape(-1, *x.shape[-2:])
            return x

        pos = ensure_nparray(pos)
        print(pos, pos.shape)

        self._get_existing_or_default(
            plugin_type=VisualisablePoints,
            name=name,
        ).set_points(pos=pos, *args, **kwargs)
