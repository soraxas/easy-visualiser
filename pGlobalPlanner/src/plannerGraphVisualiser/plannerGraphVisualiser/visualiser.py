from ._impl import *
from typing import List, Type

from .abstract_visualisable_plugin import VisualisablePlugin, ToggleableMixin


class Visualiser:
    plugin_registry: List[Type[VisualisablePlugin]] = []
    polling_registry: List[VisualisablePlugin] = []
    plugins: List[VisualisablePlugin] = []

    def __init__(self, args):
        self.args = args

        self.start_markers = None
        self.goal_markers = None
        self.axis_visual = None

        self.args.z_scaler = Zscaler(z_scale_factor=self.args.z_scale_factor)

    def initialise(self):
        self.plugins = []
        for pcls in self.plugin_registry:
            self.plugins.append(pcls(self.args))

        @self.args.canvas.connect
        def on_key_press(ev):
            for plugin in (p for p in self.plugins if isinstance(p, ToggleableMixin)):
                for registered_callback in plugin.keys:

                    if ev.key.name.upper() == registered_callback[0].upper():
                        registered_callback[2]()

    def register_plugin(self, plugin_cls: Type[VisualisablePlugin]):
        self.plugin_registry.append(plugin_cls)

    def update(self):
        for plugin in self.plugins:
            plugin.update()
