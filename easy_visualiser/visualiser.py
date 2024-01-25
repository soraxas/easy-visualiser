import dataclasses
import os
import threading
import time
from types import SimpleNamespace
from typing import Callable, Coroutine, Hashable, Iterable, List, Optional, Set, Tuple

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
    VisualisableAutoStatusBar,
    VisualisableGridLines,
    VisualisablePlugin,
    VisualisablePluginInitialisationError,
    VisualisablePrincipleAxis,
)
from .utils import ToggleableBool, topological_sort
from .visualiser_miscs import VisualiserEasyAccesserMixin, VisualiserMiscsMixin

os.putenv("NO_AT_BRIDGE", "1")

import asyncio


async def maybe_await(callback: Callable):
    # result = callback
    pass


import warnings


class HookList(dict):
    def on_event(self, ev=None):
        for hook in self.values():
            hook()

    def add_hook(self, callback: Callable, identifier: Hashable = None):
        identifier = identifier or callable

        # represent it as dict, so that it's easier to remove hook
        self[identifier] = callback

    def remove_hook(self, identifier: Hashable):
        out = self.pop(identifier, None)
        if out is None:
            warnings.warn(
                f"Given identifier '{identifier}' to remove hook, but no was found. Available: {self}."
            )
        return out


@dataclasses.dataclass
class VisualiserHooks:
    on_initialisation_finish: HookList
    on_keypress_finish: HookList
    on_visualiser_close: HookList
    on_interval_update: HookList

    def __init__(self):
        self.on_initialisation_finish = HookList()
        self.on_keypress_finish = HookList()
        self.on_visualiser_close = HookList()
        self.on_interval_update = HookList()

    @property
    def on_plugins_state_change(self) -> HookList:
        # alias
        return self.on_keypress_finish


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

    def __iter__(self):
        """Loop through stored plugins"""
        yield from self.__dict__.values()

    def _add_mapping(self, plugin: VisualisablePlugin):
        self.__dict__[plugin.name] = plugin


from .modal_control import Key
from .ufunc import PlottingUFuncMixin


class Visualiser(PlottingUFuncMixin, VisualiserMiscsMixin, VisualiserEasyAccesserMixin):
    """
    The core visualiser that can be created to represent an instance of a window
    """

    polling_registry: List[VisualisablePlugin] = []
    # raw registered plugin list
    _registered_plugins: List[Tuple[VisualisablePlugin, Set[str]]] = []
    _registered_datasources: List[DataSource] = []
    _registered_keypress_cb: List[Tuple[Key, Callable]] = []
    # sorted version
    # plugins: List[VisualisablePlugin] = []

    __closing = ToggleableBool(False)

    async_yield_sleep_time: float = 1e-6

    def register_keypress(self, key: str, callback: Callable):
        self._registered_keypress_cb.append((Key(key), callback))

    def __init__(
        self,
        title: str = "untitled",
        grid_margin: float = 0,
        bgcolor: str = "grey",
        auto_add_default_plugins: bool = True,
        type: str = "3D",
    ):
        self.app: app.Application = app.Application()

        # Display the data
        self.canvas = scene.SceneCanvas(title=title, keys="interactive", show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "turntable" if type == "3D" else "panzoom"
        self.view.camera.aspect = 1
        self.view.bgcolor = bgcolor
        self.auto_add_default_plugins = auto_add_default_plugins

        self.current_modal = ModalState(visualiser=self)
        self.hooks = VisualiserHooks()
        # build grid
        self.grid: Grid = self.canvas.central_widget.add_grid(margin=grid_margin)
        # # col num just to make it on the right size (0 is left)
        # self.grid.add_widget(col=10)

        # create an event used to stop running tasks
        self.threads = []
        self.thread_exit_event = threading.Event()
        self._registered_plugins_mappings: Optional[VisualisablePluginNameSpace] = None
        # self.initialised = False

        # self.async_loop = asyncio.get_event_loop()
        # self.async_loop.set_debug(True)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        self.async_loop = loop
        # self.async_loop.set_debug(True)
        asyncio.set_event_loop(self.async_loop)

    def _initialise_new_plugins(self):
        assert self.initialised

        _uninitialised_plugins = [
            plugin
            for plugin, _ in self._registered_plugins
            if plugin.visualiser is None
        ]

        _uninitialised_datasources = [
            d for d in self._registered_datasources if d.visualiser is None
        ]

        ###########################################################
        # on initialisation hooks
        for data_source in _uninitialised_datasources:
            data_source.on_initialisation(visualiser=self)
        # on initialisation hooks
        for plugin in _uninitialised_plugins:
            self.plugins._add_mapping(plugin)
            try:
                plugin.on_initialisation(visualiser=self)
            except VisualisablePluginInitialisationError as e:
                print(f"{plugin}: on initialisation.\n{e}")

        ###########################################################
        # build plugin
        for data_source in _uninitialised_datasources:
            data_source.construct_plugin()
        for plugin in _uninitialised_plugins:
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

        self.hooks.on_initialisation_finish.on_event()

    def initialise(self):
        """
        The initialisation function that initialise each registered plugin
        """
        if self.initialised:
            return
        self._add_default_plugins()

        self._registered_plugins_mappings = VisualisablePluginNameSpace(
            **{p.name: p for p, _ in self._registered_plugins}
        )
        ###########################################################
        # check plugin dependencies
        for plugin, deps in self._registered_plugins:
            for dep in deps:
                if dep not in self.plugins:
                    raise ValueError(
                        f"The dependency '{dep}' for plugin '{plugin.name}' "
                        f"has not been registered!"
                    )
        # sort plugins based on dependencies
        _plugins_dependency_list = [
            (
                plugin_data[0],
                set(self.plugins[dep] for dep in plugin_data[1]),
            )
            for plugin_data in self._registered_plugins
        ]

        # sorted_plugins = list(topological_sort(_plugins_dependency_list))

        self._initialise_new_plugins()

        @self.canvas.connect
        def on_key_press(ev):
            def process():
                for key, cb in self._registered_keypress_cb:
                    if key.match(ev.key.name):
                        return cb(ev)

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
            self.hooks.on_keypress_finish.on_event()
            return result

        @self.canvas.connect
        def on_close(ev):
            self.hooks.on_visualiser_close.on_event()
            self.__closing.set(True)
            self.async_loop.stop()

    def __bool__(self):
        """Represent whether this visualiser is closing or not"""
        return not bool(self.__closing)

    def register_plugin(
        self,
        plugin: VisualisablePlugin,
        depends_on: Iterable[str] = None,
        *,
        name: str = None,
    ):
        """
        Register a plugin, with an optional dependency list of plugin name.
        The other plugins that this plugin depends on will be initialised first.
        """
        if name:
            plugin.name = name
        if depends_on is None:
            depends_on = []
        depends_on = set(depends_on)
        self._registered_plugins.append((plugin, depends_on))
        if self.initialised:
            if depends_on:
                raise RuntimeError(
                    "There are dependencies given, but visualiser had already been initialised!"
                )
            self._initialise_new_plugins()

    def register_datasource(self, data_source: DataSource):
        self._registered_datasources.append(data_source)

    def interval_update(self):
        for plugin in self.plugins:
            if plugin.state is PluginState.ON:
                plugin.update()
        # TODO: move the above into using hooks.
        self.hooks.on_interval_update.on_event()

        # ##############################
        # self.async_loop.stop()
        # self.async_loop.run_forever()
        # ##############################

        # self.initialised = True

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
        for default_plugin_cls in [
            VisualisablePrincipleAxis,
            VisualisableGridLines,
            VisualisableAutoStatusBar,
        ]:
            if not any(
                type(p) == default_plugin_cls for p, _ in self._registered_plugins
            ):
                # if the plugin had already been manually added, skip it
                # note that we use type (instead of isinstance) to ignore any derived
                # class by the user. So if they derived a class, we assume that it's
                # different than the default class, so we will still add the default.
                self.register_plugin(default_plugin_cls())

    async def async_yield(self):
        await asyncio.sleep(self.async_yield_sleep_time)

    def run(self, regular_update_interval: Optional[float] = None):
        """
        The main function to start the visualisation window after everything had been
        set up.
        """

        async def core_processing():
            while self:
                app.process_events()
                self.interval_update()  # initial update
                await self.async_yield()

        # loop = asyncio.get_event_loop() # Here
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)

        self.interval_update()  # initial update
        self.async_loop.create_task(core_processing())
        self.async_loop.run_forever()

        self.thread_exit_event.set()
        for t in self.threads:
            t.join()

    def spin_once(self):
        app.process_events()
