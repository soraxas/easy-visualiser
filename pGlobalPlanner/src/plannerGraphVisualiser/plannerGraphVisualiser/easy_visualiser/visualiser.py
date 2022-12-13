from types import SimpleNamespace

import dataclasses
from vispy import scene, app

from typing import List, Tuple, Dict, Callable, Optional, Union, Iterable, Set

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
from .utils import topological_sort


@dataclasses.dataclass
class VisualiserHooks:
    on_initialisation_finish: List[Callable]
    on_keypress_finish: List[Callable]


class VisualisablePluginNameSpace(SimpleNamespace):
    def __getattr__(self, item: str) -> VisualisablePlugin:
        try:
            return self.__dict__[item]
        except KeyError:
            raise AttributeError(
                f"Plugin '{item}' has not been registered.\n"
                f"Valid options are: {[key for key in self.__dict__]}"
            )

    def __getitem__(self, item: str) -> VisualisablePlugin:
        return getattr(self, item)

    def __contains__(self, item: VisualisablePlugin) -> bool:
        return item in self.__dict__


class Visualiser:
    polling_registry: List[VisualisablePlugin] = []
    # raw registered plugin list
    _registered_plugins: List[Tuple[VisualisablePlugin, Set[str]]] = []
    # sorted version
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

        self._registered_plugins_mappings: Optional[VisualisablePluginNameSpace] = None
        self.initialised = False

    def initialise(self):

        self._registered_plugins_mappings = VisualisablePluginNameSpace(
            **{p.name: p for p, _ in self._registered_plugins}
        )
        ###########################################################
        # check plugin dependencies
        for plugin, deps in self._registered_plugins:
            for dep in deps:
                if dep not in self.registered_plugins_mappings:
                    raise ValueError(
                        f"The dependency '{dep}' for plugin '{plugin.name}' "
                        f"has not been registered!"
                    )
        # sort plugins based on dependencies
        _plugins_dependency_list = [
            (
                plugin_data[0],
                set(self.registered_plugins_mappings[dep] for dep in plugin_data[1]),
            )
            for plugin_data in self._registered_plugins
        ]

        self.plugins = list(topological_sort(_plugins_dependency_list))

        ###########################################################
        # on initialisation hooks
        for plugin in self.plugins:
            try:
                plugin.on_initialisation(visualiser=self)
            except VisualisablePluginInitialisationError as e:
                print(f"{plugin}: on initialisation.\n{e}")

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

    def register_plugin(
        self, plugin: VisualisablePlugin, depends_on: Iterable[str] = None
    ):
        if depends_on is None:
            depends_on = []
        depends_on = set(depends_on)
        self._registered_plugins.append((plugin, depends_on))

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
    def registered_plugins_mappings(self) -> VisualisablePluginNameSpace:
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
