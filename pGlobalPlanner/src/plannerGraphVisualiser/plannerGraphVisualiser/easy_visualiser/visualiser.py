from types import SimpleNamespace

import dataclasses
from vispy import scene, app

from typing import List, Tuple, Dict, Callable, Optional, Union, Iterable

from vispy.scene import Widget, Grid

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
    VisualisablePluginInitialisationError,
)
from .plugin_capability import (
    TriggerableMixin,
    WidgetsMixin,
    PluginState,
    ToggleableMixin,
)
from .modal_control import ModalControl, ModalState
from .key_mapping import Mapping


@dataclasses.dataclass
class VisualiserHooks:
    on_initialisation_finish: List[Callable]
    on_keypress_finish: List[Callable]


class Visualiser:
    polling_registry: List[VisualisablePlugin] = []
    plugins: List[VisualisablePlugin] = []

    def __init__(
        self,
        title="untitled",
        grid_margin: float = 0,
    ):
        # Display the data
        self.canvas = scene.SceneCanvas(title=title, keys="interactive", show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "turntable"
        self.view.camera.aspect = 1

        self.current_modal = ModalState(visualiser=self)
        self.hooks = VisualiserHooks([], [])
        # build grid
        self.grid: Grid = self.canvas.central_widget.add_grid(margin=grid_margin)
        # # col num just to make it on the right size (0 is left)
        # self.grid.add_widget(col=10)

        self._registered_plugins_mappings: Optional[SimpleNamespace] = None
        self.initialised = False

    def initialise(self):
        ###########################################################
        # on initialisation hooks
        for plugin in self.plugins:
            try:
                plugin.on_initialisation(visualiser=self)
            except VisualisablePluginInitialisationError as e:
                print(f"{plugin}: on initialisation.\n{e}")
        self._registered_plugins_mappings = SimpleNamespace(
            **{p.name: p for p in self.plugins}
        )

        ###########################################################
        # build plugin
        for plugin in self.plugins:
            try:
                ###########################################################
                # build widget
                if isinstance(plugin, WidgetsMixin):
                    widget_datapack = plugin.get_constructed_widgets()
                    if not isinstance(widget_datapack, list):
                        widget_datapack = [widget_datapack]
                    for widget_datapack in widget_datapack:
                        if isinstance(widget_datapack, tuple):
                            widget, data = widget_datapack
                        elif isinstance(widget_datapack, Widget):
                            widget = widget_datapack
                            data = dict()
                        else:
                            raise ValueError(
                                f"Unknown widget data type {widget_datapack}"
                            )
                        self.grid.add_widget(widget, **data)
                ###########################################################
                # extract root mappings

                ###########################################################
                # construct actual plugin
                plugin.construct_plugin()
                # plugin.state = PluginState.OFF
                ###########################################################

            except VisualisablePluginInitialisationError as e:
                print(str(e))

        for hook in self.hooks.on_initialisation_finish:
            hook()

        @self.canvas.connect
        def on_key_press(ev):
            def process():
                # print(ev.key.name)
                for _plugin in (
                    p for p in self.plugins if isinstance(p, TriggerableMixin)
                ):
                    if isinstance(_plugin, ToggleableMixin) and not bool(_plugin.state):
                        # is off. skip key matching
                        continue

                    if (
                        not self.current_modal.at_root
                        and self.current_modal.quit_key.match(ev.key.name)
                    ):
                        self.current_modal.quit_modal()
                        return True
                    for mappings in self.current_modal.state.mappings:
                        if mappings.key.match(ev.key.name):
                            mappings.callback()
                            return True

            result = process()
            for _hook in self.hooks.on_keypress_finish:
                _hook()
            return result

    def register_plugin(self, plugin: VisualisablePlugin):
        self.plugins.append(plugin)

    def interval_update(self):
        for plugin in self.plugins:
            if plugin.state is PluginState.ON:
                plugin.update()
        self.initialised = True

    @property
    def triggerable_plugins(
        self,
    ) -> Iterable[Union[VisualisablePlugin, TriggerableMixin]]:
        yield from (p for p in self.plugins if isinstance(p, TriggerableMixin))

    @property
    def registered_plugins_mappings(self) -> SimpleNamespace:
        if self._registered_plugins_mappings is None:
            raise RuntimeError("Visualiser has not been initialised yet!")
        return self._registered_plugins_mappings

    def run(self, regular_update_interval: Optional[float] = None):
        if regular_update_interval:
            timer = app.Timer(
                interval=regular_update_interval,
                connect=lambda ev: self.interval_update(),
                start=True,
            )
        self.interval_update()  # initial update
        app.run()
