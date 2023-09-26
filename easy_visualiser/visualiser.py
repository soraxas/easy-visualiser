import dataclasses
import os
import threading
import time
from types import SimpleNamespace
from typing import Callable, Coroutine, Iterable, List, Optional, Set, Tuple, Union

from vispy import app, scene
from vispy.scene import Grid, Widget

from .input import DataSource
from .modal_control import ModalState
from .plugin_capability import (
    PluginState,
    ToggleableMixin,
    TriggerableMixin,
    WidgetsMixin,
)
from .plugins import (
    VisualisableGridLines,
    VisualisablePlugin,
    VisualisablePluginInitialisationError,
    VisualisablePrincipleAxis,
)
from .utils import topological_sort

os.putenv("NO_AT_BRIDGE", "1")

import asyncio


async def maybe_await(callback: Callable):
    # result = callback
    pass


@dataclasses.dataclass
class VisualiserHooks:
    on_initialisation_finish: List[Callable]
    on_keypress_finish: List[Callable]


class VisualisablePluginNameSpace(SimpleNamespace):
    """
    Simple namespace to allow each plugin to refer to other plugins
    """

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
    """
    The core visualiser that can be created to represent an instance of a window
    """

    polling_registry: List[VisualisablePlugin] = []
    # raw registered plugin list
    _registered_plugins: List[Tuple[VisualisablePlugin, Set[str]]] = []
    _registered_datasources: List[DataSource] = []
    # sorted version
    plugins: List[VisualisablePlugin] = []

    def __init__(
        self,
        title="untitled",
        grid_margin: float = 0,
        bgcolor: str = "grey",
        auto_add_default_plugins: bool = True,
    ):
        # Display the data
        self.canvas = scene.SceneCanvas(title=title, keys="interactive", show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "turntable"
        self.view.camera.aspect = 1
        self.view.bgcolor = bgcolor
        self.auto_add_default_plugins = auto_add_default_plugins

        self.current_modal = ModalState(visualiser=self)
        self.hooks = VisualiserHooks([], [])
        # build grid
        self.grid: Grid = self.canvas.central_widget.add_grid(margin=grid_margin)
        # # col num just to make it on the right size (0 is left)
        # self.grid.add_widget(col=10)

        # create an event used to stop running tasks
        self.threads = []
        self.thread_exit_event = threading.Event()
        self._registered_plugins_mappings: Optional[VisualisablePluginNameSpace] = None
        self.initialised = False

        self.async_loop = asyncio.get_event_loop()
        self.async_loop.set_debug(True)

    def initialise(self):
        """
        The initialisation function that initialise each registered plugin
        """
        self._add_default_plugins()

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
        for data_source in self._registered_datasources:
            data_source.on_initialisation(visualiser=self)
        # on initialisation hooks
        for plugin in self.plugins:
            try:
                plugin.on_initialisation(visualiser=self)
            except VisualisablePluginInitialisationError as e:
                print(f"{plugin}: on initialisation.\n{e}")

        ###########################################################
        # build plugin
        for data_source in self._registered_datasources:
            data_source.construct_plugin()
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
                    if isinstance(_plugin, ToggleableMixin) and _plugin.state.is_off():
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
        """
        Register a plugin, with an optional dependency list of plugin name.
        The other plugins that this plugin depends on will be initialised first.
        """
        if depends_on is None:
            depends_on = []
        depends_on = set(depends_on)
        self._registered_plugins.append((plugin, depends_on))

    def register_datasource(self, data_source: DataSource):
        self._registered_datasources.append(data_source)

    def interval_update(self):
        for plugin in self.plugins:
            if plugin.state is PluginState.ON:
                plugin.update()

        # ##############################
        # self.async_loop.stop()
        # self.async_loop.run_forever()
        # ##############################

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

    @property
    def visual_parent(self):
        """An easy way to reference the parent of all visual elements."""
        return self.view.scene

    def add_coroutine_task(self, func: Coroutine):
        self.async_loop.create_task(func)

    def run_in_background_thread(self, func: Callable, run_every: float):
        return
        self.threads.append(
            threading.Thread(target=self.__thread_runner, args=(func, run_every))
        )
        # return
        self.threads[-1].start()

        # import asyncio
        # async def task():
        #         print("start")
        #         await asyncio.sleep(.6)
        #         print("mid")
        #         await asyncio.sleep(10)
        #         print("end")

        # # # self.async_task = asyncio.create_task(task())
        # loop = asyncio.get_event_loop()
        # loop.set_debug(True)

        # # # async def create_tasks_func():
        # # #     tasks = list()
        # # #     for i in range(5):
        # # #         tasks.append(asyncio.create_task(func(i)))
        # # #     await asyncio.wait(tasks)
        # # loop.run_until_complete(task())

        # print(loop.is_running())

        # async def main():
        #     await asyncio.sleep(1)
        #     print('hello')

        # # asyncio.run(task())

        # loop.create_task(task())

        # loop.stop()
        # loop.run_forever()
        # print("=========")
        # import time
        # time.sleep(.5)

        # loop.stop()
        # loop.run_forever()
        # print("=========")
        # import time
        # time.sleep(.2)

        # loop.stop()
        # loop.run_forever()
        # print("=========")
        # loop.stop()
        # loop.run_forever()
        # print("=========")

    def __thread_runner(self, func: Callable, run_every: float):
        while not self.thread_exit_event.is_set():
            func()
            time.sleep(run_every)

    def _add_default_plugins(self):
        if not self.auto_add_default_plugins:
            return
        for default_plugin_cls in [VisualisablePrincipleAxis, VisualisableGridLines]:
            if not any(
                type(p) == default_plugin_cls for p, _ in self._registered_plugins
            ):
                # if the plugin had already been manually added, skip it
                # note that we use type (instead of isinstance) to ignore any derived
                # class by the user. So if they derived a class, we assume that it's
                # different than the default class, so we will still add the default.
                self.register_plugin(default_plugin_cls())

    def async_interval_update(self):
        # process all scheduled callbacks
        self.async_loop.stop()
        self.async_loop.run_forever()
        # print('-', end='')
        # import sys
        # sys.stdout.flush()

    def run(self, regular_update_interval: Optional[float] = None):
        """
        The main function to start the visualisation window after everything had been
        set up.
        """

        asyncio_event_loop_timer = app.Timer(
            interval=0.2,
            connect=lambda ev: self.async_interval_update(),
            start=True,
        )

        if regular_update_interval:
            timer = app.Timer(
                interval=regular_update_interval,
                connect=lambda ev: self.interval_update(),
                start=True,
            )
        self.interval_update()  # initial update
        app.run()
        self.thread_exit_event.set()
        for t in self.threads:
            t.join()
