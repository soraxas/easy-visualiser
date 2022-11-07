from types import SimpleNamespace

import dataclasses
from vispy import scene, app

from typing import List, Tuple, Dict, Callable, Optional

from plannerGraphVisualiser.easy_visualiser.plugins.abstract_visualisable_plugin import (
    VisualisablePlugin,
    VisualisablePluginInitialisationError,
)
from .plugin_capability import ToggleableMixin, WidgetsMixin, PluginState, WidgetOption
from .modal_control import ModalControl, ModalState


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
    ):
        # Display the data
        self.canvas = scene.SceneCanvas(title=title, keys="interactive", show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "turntable"
        self.view.camera.aspect = 1

        self.current_modal = ModalState()
        self.hooks = VisualiserHooks([], [])
        # build grid
        self.grid = self.canvas.central_widget.add_grid(margin=10)
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
                    for widget, data in plugin.get_constructed_widgets():
                        self.grid.add_widget(widget, **data)
                ###########################################################
                # construct actual plugin
                if plugin.construct_plugin():
                    plugin.state = PluginState.OFF
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
                    p for p in self.plugins if isinstance(p, ToggleableMixin)
                ):

                    if self.current_modal.state is None:
                        # selecting modal
                        for registered_modal in _plugin.keys:

                            if isinstance(registered_modal, tuple):
                                continue
                            registered_modal: ModalControl

                            if registered_modal.key.match(ev.key.name):
                                self.current_modal.state = registered_modal
                                return True
                    else:
                        # operating within modal
                        if ModalState.quit_key.match(ev.key.name):
                            self.current_modal.state = None
                            return True
                        for mappings in self.current_modal.state.mappings:
                            if mappings.key.match(ev.key.name.upper()):
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
